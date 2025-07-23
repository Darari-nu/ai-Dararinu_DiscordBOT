"""
記事抽出ユーティリティ
URL から記事本文を抽出する機能を提供
"""

import re
import aiohttp
import asyncio
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from readability import Document
import logging

logger = logging.getLogger(__name__)

class ArticleExtractor:
    """WEBページから記事本文を抽出するクラス"""
    
    def __init__(self):
        self.max_content_length = 12000  # 12k字上限
        self.timeout = 30  # 30秒タイムアウト
        
    def extract_urls_from_text(self, text: str) -> list[str]:
        """テキストからURLを抽出"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    async def fetch_article_content(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        URLから記事コンテンツを取得
        
        Returns:
            Tuple[title, content, error_message]
        """
        try:
            # URLの基本的な検証
            if not self._is_valid_url(url):
                return None, None, "無効なURLです"
            
            # HTTPリクエスト実行
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return None, None, f"HTTPエラー: {response.status}"
                    
                    # コンテンツタイプチェック
                    content_type = response.headers.get('content-type', '')
                    if 'text/html' not in content_type:
                        return None, None, "HTMLコンテンツではありません"
                    
                    # 文字エンコーディングを自動検出して読み込み
                    try:
                        html = await response.text()
                    except UnicodeDecodeError:
                        # UTF-8で読めない場合は、バイト読み込み→文字エンコーディング検出
                        html_bytes = await response.read()
                        try:
                            # chardetがインストールされている場合は使用
                            import chardet
                            detected = chardet.detect(html_bytes)
                            encoding = detected.get('encoding', 'utf-8')
                            logger.info(f"文字エンコーディング検出: {encoding}")
                            html = html_bytes.decode(encoding, errors='ignore')
                        except ImportError:
                            # chardetがない場合は一般的なエンコーディングを試行
                            logger.warning("chardetがインストールされていません。フォールバック処理を実行")
                            encodings = ['shift-jis', 'euc-jp', 'iso-2022-jp', 'utf-8']
                            html = None
                            for enc in encodings:
                                try:
                                    html = html_bytes.decode(enc, errors='ignore')
                                    logger.info(f"エンコーディング {enc} で読み込み成功")
                                    break
                                except Exception:
                                    continue
                            if html is None:
                                html = html_bytes.decode('utf-8', errors='ignore')
                        except Exception as e:
                            logger.warning(f"文字エンコーディング検出エラー: {e}")
                            # 最終的にはShift-JISを試行
                            try:
                                html = html_bytes.decode('shift-jis', errors='ignore')
                            except Exception:
                                html = html_bytes.decode('utf-8', errors='ignore')
                    
            # 記事本文を抽出
            title, content = self._extract_article_from_html(html)
            
            if not content:
                return None, None, "記事本文を抽出できませんでした"
            
            if len(content) < 500:
                return None, None, "記事が短すぎます（500文字未満）"
            
            # 文字数制限
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "..."
            
            return title, content, None
            
        except asyncio.TimeoutError:
            return None, None, "リクエストがタイムアウトしました"
        except aiohttp.ClientError as e:
            return None, None, f"ネットワークエラー: {str(e)}"
        except Exception as e:
            logger.error(f"記事取得エラー: {str(e)}")
            return None, None, f"予期しないエラーが発生しました: {str(e)}"
    
    def _is_valid_url(self, url: str) -> bool:
        """URLの基本的な検証"""
        if not url or len(url) > 2000:
            return False
        
        # 基本的なURL形式チェック
        url_pattern = r'^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'
        
        if not re.match(url_pattern, url):
            return False
        
        # 除外するドメイン/パターン
        excluded_patterns = [
            r'localhost',
            r'127\.0\.0\.1',
            r'192\.168\.',
            r'10\.',
            r'172\.(1[6-9]|2[0-9]|3[0-1])\.',
            r'\.onion$',
            r'javascript:',
            r'data:',
            r'ftp://',
        ]
        
        for pattern in excluded_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
    
    def _extract_article_from_html(self, html: str) -> Tuple[Optional[str], Optional[str]]:
        """HTMLから記事本文を抽出"""
        try:
            # readabilityで記事コンテンツを抽出
            doc = Document(html)
            title = doc.title()
            content_html = doc.summary()
            
            # BeautifulSoupでHTMLタグを除去
            soup = BeautifulSoup(content_html, 'html.parser')
            
            # スクリプトやスタイルタグを除去
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # テキスト抽出
            content = soup.get_text()
            
            # テキスト整形
            content = self._clean_text(content)
            
            return title, content
            
        except Exception as e:
            logger.error(f"HTML解析エラー: {str(e)}")
            return None, None
    
    def _clean_text(self, text: str) -> str:
        """テキストの整形"""
        if not text:
            return ""
        
        # 複数の改行を単一の改行に
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # 連続する空白を単一の空白に
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 行頭行末の空白を除去
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)
        
        return text.strip()

# グローバルインスタンス
article_extractor = ArticleExtractor()