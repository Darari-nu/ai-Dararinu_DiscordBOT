print("DEBUG: main.py開始", flush=True)
import discord
from discord.ext import commands
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import requests
from datetime import datetime, timezone, timedelta
import logging
import asyncio
import tempfile
from pydub import AudioSegment
import re
import aiohttp
import time
import subprocess
import io
from utils.article_extractor import article_extractor
from deep_translator import GoogleTranslator
from typing import Optional

# URL検出関数
def contains_url(text):
    """メッセージにURLが含まれているかチェック"""
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, text))

def is_url_only_message(text):
    """URLのみのメッセージかチェック（前後に少しのテキストは許可）"""
    url_pattern = r'https?://[^\s]+'
    # まずURLが含まれているかチェック
    if not re.search(url_pattern, text):
        return False
    # URLを除去した残りのテキストをチェック
    text_without_urls = re.sub(url_pattern, '', text).strip()
    return len(text_without_urls) <= 20  # 20文字以下なら「URLのみ」とみなす

def extract_urls_from_text(text):
    """テキストからURLを抽出"""
    url_pattern = r'https?://[^\s]+'
    return re.findall(url_pattern, text)

def is_english_title(title):
    """タイトルが英語かどうかを判定"""
    if not title:
        return False
    
    # 英語文字（アルファベット）の割合を計算
    english_chars = sum(1 for c in title if c.isalpha() and ord(c) < 128)
    total_chars = sum(1 for c in title if c.isalpha())
    
    if total_chars == 0:
        return False
    
    english_ratio = english_chars / total_chars
    
    # 70%以上が英語文字なら英語タイトルと判定
    return english_ratio >= 0.7

def extract_text_from_html(html_content):
    """HTMLから本文テキストを抽出"""
    if not html_content:
        return ""
    
    # CSS styleタグを除去
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # CSS linkタグを除去
    text = re.sub(r'<link[^>]*>', '', text, flags=re.IGNORECASE)
    
    # JavaScript scriptタグを除去
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # JSON-LD scriptタグを除去
    text = re.sub(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # CSS内のクラス名やスタイル定義を除去
    text = re.sub(r'[^}]*{[^}]*}', '', text)
    
    # BRタグを改行に変換
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    
    # Pタグの終了を改行に変換
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    
    # 見出しタグの終了を改行に変換
    text = re.sub(r'</h[1-6]>', '\n\n', text, flags=re.IGNORECASE)
    
    # divタグの終了を改行に変換
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    
    # その他のHTMLタグを除去
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3つ以上の連続改行を2つに制限
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 各行の前後の空白を削除
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)
    
    # 空行を削除してから結合
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

async def fetch_url_content(url):
    """URLからコンテンツを取得してテキストを抽出"""
    try:
        # curlコマンドを使用してHTTPSサイトから取得（30秒タイムアウト）
        # Windows環境での文字化け対策: UTF-8エンコーディングを明示
        result = subprocess.run(['curl', '-s', url], capture_output=True, timeout=30, encoding='utf-8', errors='replace')
        
        if result.returncode != 0:
            logger.error(f"Curl Error: {result.stderr}")
            return None
        
        html_content = result.stdout
        
        # 本文を抽出
        text_content = extract_text_from_html(html_content)
        
        return text_content
        
    except subprocess.TimeoutExpired:
        logger.error(f"URL取得タイムアウト (30秒): {url}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"文字コードエラー: {e}")
        # フォールバック: バイナリで取得してデコード試行
        try:
            result = subprocess.run(['curl', '-s', url], capture_output=True, timeout=30)
            # UTF-8で試行、ダメならcp932、それでもダメなら無視
            try:
                html_content = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    html_content = result.stdout.decode('cp932')
                except UnicodeDecodeError:
                    html_content = result.stdout.decode('utf-8', errors='ignore')
            
            text_content = extract_text_from_html(html_content)
            return text_content
        except Exception as fallback_error:
            logger.error(f"フォールバック処理エラー: {fallback_error}")
            return None
    except Exception as e:
        logger.error(f"URL取得エラー: {e}")
        return None

# スクリプトのディレクトリを基準に.envファイルを読み込む
script_dir = Path(__file__).parent
env_path = script_dir / '.env'

# 必要なディレクトリを自動作成
def create_required_directories():
    """起動時に必要なディレクトリを自動作成"""
    required_dirs = [
        script_dir / "data" / "server_data",
        script_dir / "data" / "user_data", 
        script_dir / "attachments"
    ]
    
    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 ディレクトリ確認: {dir_path}")

# 必要なディレクトリを作成
create_required_directories()

# 既存の環境変数をクリアしてから.envファイルを読み込む
if 'OPENAI_API_KEY' in os.environ:
    del os.environ['OPENAI_API_KEY']
if 'DISCORD_BOT_TOKEN' in os.environ:
    del os.environ['DISCORD_BOT_TOKEN']

load_dotenv(env_path, override=True)

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# デバッグ情報
print(f"DEBUG: .env path = {env_path}")
print(f"DEBUG: .env exists = {env_path.exists()}")
print(f"DEBUG: TOKEN length = {len(TOKEN) if TOKEN else 'None'}")
print(f"DEBUG: OPENAI_API_KEY length = {len(OPENAI_API_KEY) if OPENAI_API_KEY else 'None'}")

# OpenAIモデル設定
FREE_USER_MODEL = "gpt-4.1-mini"
PREMIUM_USER_MODEL = "gpt-4.1"

# テストサーバーID（スラッシュコマンドの即座反映用）
# Botが参加しているサーバーのIDに変更してください
TEST_GUILD_ID = 1073542600033849446  # Botがこのサーバーに招待されている必要があります

# settings.jsonから設定を読み込む
settings_path = script_dir / "settings.json"
if settings_path.exists():
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
        FREE_USER_DAILY_LIMIT = settings.get("free_user_daily_limit", 5)
else:
    FREE_USER_DAILY_LIMIT = 5  # デフォルト値

def is_english_content(text):
    """コンテンツが英語かどうかを判定"""
    try:
        # フォールバック: 英語文字の比率で判定
        if not text:
            return False
        english_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_chars = sum(1 for c in text if c.isalpha())
        if total_chars == 0:
            return False
        english_ratio = english_chars / total_chars
        return english_ratio >= 0.7
    except Exception:
        return False

async def translate_text_to_japanese(text):
    """テキストを日本語に翻訳（非同期対応）"""
    try:
        # 長いテキストは文単位で分割して翻訳
        max_length = 2000  # より安全な制限値
        
        if len(text) <= max_length:
            # 短いテキストはそのまま翻訳
            translator = GoogleTranslator(source='en', target='ja')
            translated = translator.translate(text)
            return translated
        else:
            # 長いテキストは文単位で分割
            sentences = []
            # 段落単位で分割し、さらに文単位に分割
            paragraphs = text.split('\n\n')
            
            for paragraph in paragraphs:
                # 文単位で分割（.や!、?で区切る）
                import re
                paragraph_sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                sentences.extend(paragraph_sentences)
            
            translated_sentences = []
            current_batch = ""
            translator = GoogleTranslator(source='en', target='ja')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # バッチサイズを確認
                if len(current_batch + ' ' + sentence) <= max_length:
                    current_batch = (current_batch + ' ' + sentence).strip()
                else:
                    # 現在のバッチを翻訳
                    if current_batch:
                        try:
                            translated = translator.translate(current_batch)
                            translated_sentences.append(translated)
                        except Exception as batch_error:
                            logger.warning(f"バッチ翻訳エラー: {batch_error}")
                            # 個別の文を翻訳試行
                            batch_sentences = current_batch.split('. ')
                            for individual_sentence in batch_sentences:
                                try:
                                    if individual_sentence.strip():
                                        individual_translated = translator.translate(individual_sentence.strip())
                                        translated_sentences.append(individual_translated)
                                except Exception:
                                    translated_sentences.append(individual_sentence)  # 翻訳失敗時は原文
                    
                    current_batch = sentence
            
            # 最後のバッチを処理
            if current_batch:
                try:
                    translated = translator.translate(current_batch)
                    translated_sentences.append(translated)
                except Exception as final_error:
                    logger.warning(f"最終バッチ翻訳エラー: {final_error}")
                    translated_sentences.append(current_batch)  # 翻訳失敗時は原文
            
            return ' '.join(translated_sentences)
            
    except Exception as e:
        logger.error(f"翻訳エラー: {e}")
        return text  # 翻訳失敗時は元のテキストを返す

async def generate_thread_image(first_tweet_content: str) -> Optional[str]:
    """1ツイート目の内容から粘土フィギュア質感の画像を生成"""
    try:
        # 1ツイート目から視覚的要素を抽出
        response = client_openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an image-prompt generator. Analyze the tweet content and extract visual elements that can be rendered as clay figures. Return only the visual elements string."
                },
                {
                    "role": "user", 
                    "content": f"""Analyze this tweet and extract visual elements for image generation:

Tweet: {first_tweet_content}

Extract visual elements focusing on:
- Main subjects (people, objects, characters)
- Actions and expressions  
- Environment and setting
- Key props and tools
- Atmosphere and mood

Return format: "subject doing action in environment with props, specific mood"
Example: "game developer focused on character modeling at computer workstation with sculpting tools, creative atmosphere"

Visual elements:"""
                }
            ],
            max_tokens=80,
            temperature=0.3
        )
        
        visual_elements = response.choices[0].message.content.strip()
        logger.info(f"視覚的要素抽出結果: {visual_elements}")
        
        # 統一テンプレートで最終プロンプト構築
        enhanced_prompt = f"{visual_elements} rendered as handmade clay figures with ultra-detailed textures, natural window lighting (5500K), high quality digital art, 16:10 aspect ratio"
        
        logger.info(f"最終画像プロンプト: {enhanced_prompt}")
        
    except Exception as e:
        logger.error(f"視覚的要素抽出エラー: {e}")
        # フォールバック
        enhanced_prompt = "creative workspace scene with focused person and professional tools rendered as handmade clay figures with ultra-detailed textures, natural window lighting (5500K), high quality digital art, 16:10 aspect ratio"
    
    # OpenAI Imagen API呼び出し
    try:
        logger.info(f"画像生成開始: {enhanced_prompt}")
        
        # OpenAI Imagen API呼び出し（低品質・低コスト設定・横長）
        response = client_openai.images.generate(
            model="gpt-image-1", 
            prompt=enhanced_prompt,
            size="1536x1024",
            quality="medium",
            n=1
        )
            
        # Imagenのレスポンス処理（デバッグ情報付き）
        logger.info(f"画像生成レスポンス構造: {type(response.data)}, 長さ: {len(response.data) if response.data else 'None'}")
        
        if response.data and len(response.data) > 0:
            image_data = response.data[0]
            logger.info(f"画像データ構造: {type(image_data)}, 属性: {dir(image_data)}")
            
            # URL形式の場合（DALL-E 3パターン）
            if hasattr(image_data, 'url') and image_data.url:
                image_url = image_data.url
                logger.info(f"画像生成成功 (URL): {image_url}")
                return image_url
            
            # base64形式の場合（Imagenパターン）
            elif hasattr(image_data, 'b64_json') and image_data.b64_json:
                try:
                    import base64
                    
                    # base64データをデコード
                    image_bytes = base64.b64decode(image_data.b64_json)
                    
                    # 一時ファイルとして保存
                    temp_filename = f"temp_image_{int(time.time())}.png"
                    temp_path = script_dir / "attachments" / temp_filename
                    
                    # attachmentsディレクトリを作成（存在しない場合）
                    temp_path.parent.mkdir(exist_ok=True)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    logger.info(f"画像生成成功 (base64): 一時ファイル {temp_path} に保存")
                    return str(temp_path)
                    
                except Exception as e:
                    logger.error(f"base64画像処理エラー: {e}")
                    return None
            
            else:
                logger.error(f"画像生成: 不明なレスポンス形式")
                logger.error(f"image_data内容: {image_data}")
                return None
        else:
            logger.error(f"画像生成: 空のレスポンス - response.data: {response.data}")
            return None
            
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        # OpenAIの安全システムエラーの場合は詳細をログに記録
        if "safety system" in str(e) or "content_policy_validation" in str(e):
            logger.warning(f"OpenAI安全システムによる画像生成拒否: {enhanced_prompt}")
        return None

# カスタムログハンドラー（書き込み時のみファイルを開く）
class SyncFriendlyFileHandler(logging.Handler):
    def __init__(self, filename, encoding='utf-8', max_bytes=10*1024*1024):
        super().__init__()
        self.filename = filename
        self.encoding = encoding
        self.max_bytes = max_bytes
        
    def emit(self, record):
        try:
            # ファイルサイズチェック（ローテーション）
            if Path(self.filename).exists() and Path(self.filename).stat().st_size > self.max_bytes:
                self._rotate_logs()
            
            # 書き込み時のみファイルを開く
            with open(self.filename, 'a', encoding=self.encoding) as f:
                f.write(self.format(record) + '\n')
                f.flush()  # 即座に書き込み
        except Exception:
            self.handleError(record)
    
    def _rotate_logs(self):
        """ログファイルをローテーション"""
        try:
            base_path = Path(self.filename)
            # 古いバックアップを削除・移動
            for i in range(4, 0, -1):  # log.txt.4 → log.txt.5
                old_file = base_path.with_suffix(f'.txt.{i}')
                new_file = base_path.with_suffix(f'.txt.{i+1}')
                if old_file.exists():
                    if new_file.exists():
                        new_file.unlink()
                    old_file.rename(new_file)
            
            # 現在のログファイルをlog.txt.1に移動
            if base_path.exists():
                backup_file = base_path.with_suffix('.txt.1')
                if backup_file.exists():
                    backup_file.unlink()
                base_path.rename(backup_file)
        except Exception as e:
            print(f"ログローテーションエラー: {e}")

# ログ設定（同期フレンドリー）
log_file = script_dir / "log.txt"
sync_handler = SyncFriendlyFileHandler(log_file)
sync_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        sync_handler,
        logging.StreamHandler()  # コンソールにも出力
    ]
)
logger = logging.getLogger(__name__)

# 統計管理クラス
class StatsManager:
    def __init__(self):
        self.stats_dir = script_dir / "data" / "activity_logs"
        self.stats_dir.mkdir(exist_ok=True)
        logger.info("統計管理システムを初期化しました")
    
    async def record_user_activity(self, user_id, bot_instance=None):
        """ユーザーアクティビティをリアルタイム記録"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.stats_dir / f"{today}.json"
            
            # 今日のログを読み込み
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # 新しい日の最初の記録時にサーバー数を記録
                server_count = len(bot_instance.guilds) if bot_instance else 0
                data = {
                    "date": today,
                    "active_users": [],
                    "total_actions": 0,
                    "server_count": server_count
                }
                logger.info(f"新しい日の統計開始: サーバー数 {server_count}")
            
            # ユーザーを追加（重複なし）
            if user_id not in data["active_users"]:
                data["active_users"].append(user_id)
                logger.debug(f"新規アクティブユーザー記録: {user_id}")
            
            data["total_actions"] += 1
            
            # ログファイルに保存
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"アクティビティ記録エラー: {e}")
    
    def calculate_dau(self, target_date=None):
        """指定日のDAU計算（デフォルトは今日）"""
        try:
            if target_date is None:
                target_date = datetime.now().strftime("%Y-%m-%d")
            
            log_file = self.stats_dir / f"{target_date}.json"
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return len(data.get("active_users", []))
            return 0
            
        except Exception as e:
            logger.error(f"DAU計算エラー: {e}")
            return 0
    
    def calculate_mau(self, target_date=None):
        """指定日から過去30日間のMAU計算"""
        try:
            if target_date is None:
                base_date = datetime.now()
            else:
                base_date = datetime.strptime(target_date, "%Y-%m-%d")
            
            mau_users = set()
            
            for i in range(30):
                date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
                log_file = self.stats_dir / f"{date}.json"
                
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        mau_users.update(data.get("active_users", []))
            
            return len(mau_users)
            
        except Exception as e:
            logger.error(f"MAU計算エラー: {e}")
            return 0
    
    def get_stats_summary(self):
        """統計サマリーを取得"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            dau = self.calculate_dau()
            mau = self.calculate_mau()
            
            # 総アクション数・サーバー数（今日）
            today_log = self.stats_dir / f"{today}.json"
            total_actions_today = 0
            server_count_today = 0
            if today_log.exists():
                with open(today_log, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    total_actions_today = data.get("total_actions", 0)
                    server_count_today = data.get("server_count", 0)
            
            return {
                "date": today,
                "dau": dau,
                "mau": mau,
                "total_actions_today": total_actions_today,
                "server_count": server_count_today
            }
            
        except Exception as e:
            logger.error(f"統計サマリー取得エラー: {e}")
            return {"date": "", "dau": 0, "mau": 0, "total_actions_today": 0, "server_count": 0}

# OpenAIクライアントの初期化（60秒タイムアウト設定）
client_openai = None
if OPENAI_API_KEY:
    client_openai = OpenAI(
        api_key=OPENAI_API_KEY,
        timeout=180.0  # 180秒タイムアウト（長い音声ファイル対応）
    )


# Intentsの設定（Discord Developer Portalで有効化が必要）
intents = discord.Intents.default()
# 以下のIntentsはDiscord Developer Portal -> Bot -> Privileged Gateway Intentsで有効化が必要
intents.message_content = True  # MESSAGE CONTENT INTENT
intents.reactions = True
intents.members = True  # SERVER MEMBERS INTENT

# Botの初期化
bot = commands.Bot(command_prefix='!', intents=intents)

# 統計管理インスタンスを作成
stats_manager = StatsManager()
print("DEBUG: StatsManager作成完了", flush=True)


def load_server_data(server_id):
    """サーバーデータを読み込む"""
    file_path = script_dir / "data" / "server_data" / f"{server_id}.json"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_server_data(server_id, data):
    """サーバーデータを保存する"""
    data_dir = script_dir / "data" / "server_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"{server_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_channel_active(server_id, channel_id):
    """チャンネルが有効かどうかをチェック"""
    server_data = load_server_data(server_id)
    if server_data and 'active_channel_ids' in server_data:
        return str(channel_id) in server_data['active_channel_ids']
    return False

def migrate_user_data(user_data, user_id, username):
    """古いユーザーデータを新しいフォーマットにマイグレーション"""
    # 必要なフィールドのデフォルト値
    default_fields = {
        "user_id": str(user_id),
        "username": username,
        "custom_prompt_x_post": "",
        "custom_prompt_article": "",
        "custom_prompt_memo": "",
        "status": "free",
        "last_used_date": "",
        "daily_usage_count": 0
    }
    
    # 不足しているフィールドを追加
    updated = False
    for field, default_value in default_fields.items():
        if field not in user_data:
            user_data[field] = default_value
            updated = True
            logger.info(f"マイグレーション: ユーザー {user_id} に {field} フィールドを追加")
    
    # 古いフィールド名の変換
    if "custom_x_post_prompt" in user_data:
        user_data["custom_prompt_x_post"] = user_data.pop("custom_x_post_prompt")
        updated = True
        logger.info(f"マイグレーション: ユーザー {user_id} の custom_x_post_prompt を custom_prompt_x_post に変換")
    
    return user_data, updated

async def check_content_for_urls(content_text, user, channel):
    """コンテンツ内のURLを検出し、必要に応じて警告を表示"""
    import re
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, content_text) if content_text else []
    
    if urls:
        warning_msg = (
            f"{user.mention} ⚠️ URLが含まれたコンテンツを検出しました\n"
            f"📝 URLの中身は読み取ることができませんが、このまま処理を続行します\n"
            f"🔗 検出されたURL: {len(urls)}個"
        )
        await channel.send(warning_msg)
    
    return content_text

def load_user_data(user_id):
    """ユーザーデータを読み込む"""
    file_path = script_dir / "data" / "user_data" / f"{user_id}.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"ユーザーデータ読み込みエラー {user_id}: {e}")
            return None
    return None

def save_user_data(user_id, data):
    """ユーザーデータを保存する"""
    data_dir = script_dir / "data" / "user_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"{user_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def is_premium_user(user_id):
    """ユーザーがプレミアムかどうかを判定"""
    try:
        # オーナーチェック（設定ファイルベース）- 最優先
        owner_user_id = settings.get("owner_user_id")
        if owner_user_id and str(user_id) == str(owner_user_id):
            logger.info(f"User {user_id} is configured owner - granting premium access")
            return True
        
        # サーバーオーナーの特別判定
        community_guild = bot.get_guild(int(settings.get("community_server_id")))
        if not community_guild:
            logger.warning(f"Community server not found: {settings.get('community_server_id')}")
            # コミュニティサーバーが見つからなくても、設定ファイルベースのオーナー判定は上で実行済み
            return False
        
        # オーナーチェック（Discord APIベース）
        if int(user_id) == community_guild.owner_id:
            logger.info(f"User {user_id} is server owner - granting premium access")
            return True
        
        logger.info(f"Debug: Checking user {user_id} in guild {community_guild.name}")
        
        member = community_guild.get_member(int(user_id))
        if not member:
            logger.info(f"User {user_id} not found in cache, trying to fetch from API...")
            try:
                # キャッシュにない場合はAPIから直接取得を試す
                member = await community_guild.fetch_member(int(user_id))
                logger.info(f"Successfully fetched user {user_id} from API")
            except discord.NotFound:
                logger.warning(f"User {user_id} not found in community server {community_guild.name}")
                logger.info(f"Debug: Guild has {community_guild.member_count} members")
                return False
            except discord.Forbidden:
                logger.warning(f"Permission denied when fetching user {user_id} from community server")
                logger.info(f"Debug: This may be due to insufficient bot permissions")
                return False
            except Exception as e:
                logger.error(f"Error fetching user {user_id}: {e}")
                return False
        
        logger.info(f"Debug: Found member {member.name}#{member.discriminator}")
        logger.info(f"Debug: Member roles: {[f'{role.name}({role.id})' for role in member.roles]}")
        
        # プレミアムロールの確認
        premium_role_id = int(settings.get("premium_role_id"))
        logger.info(f"Debug: Looking for premium role ID: {premium_role_id}")
        
        has_premium_role = any(role.id == premium_role_id for role in member.roles)
        
        logger.info(f"Premium check for user {user_id} ({member.name}): {has_premium_role}")
        return has_premium_role
        
    except Exception as e:
        logger.error(f"Error checking premium status for user {user_id}: {e}")
        return False

def can_use_feature(user_data, is_premium):
    """機能使用可能かチェックし、使用回数を更新"""
    # 日本時間（JST）で現在の日付を取得
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).strftime("%Y-%m-%d")
    
    # プレミアムユーザーは無制限（ただし使用回数はカウント）
    if is_premium:
        last_used_date = user_data.get("last_used_date", "")
        daily_usage_count = user_data.get("daily_usage_count", 0)
        
        # 日付が変わった場合はカウントをリセット
        if last_used_date != today:
            user_data["last_used_date"] = today
            user_data["daily_usage_count"] = 1
        else:
            # 同じ日の場合は使用回数を増加
            user_data["daily_usage_count"] = daily_usage_count + 1
        
        return True, None
    
    # 無料ユーザーの制限チェック
    last_used_date = user_data.get("last_used_date", "")
    daily_usage_count = user_data.get("daily_usage_count", 0)
    
    # 日付が変わった場合はカウントをリセット
    if last_used_date != today:
        user_data["last_used_date"] = today
        user_data["daily_usage_count"] = 1
        return True, None
    
    # 同じ日の場合は制限チェック
    if daily_usage_count >= FREE_USER_DAILY_LIMIT:
        return False, f"😅 今日の分の利用回数を使い切っちゃいました！\n無料プランでは1日{FREE_USER_DAILY_LIMIT}回まで利用できます。明日また遊びに来てくださいね！✨\n\n💎 **もっと使いたい場合は有料プランがおすすめです！**\n🤖 このBotのプロフィールを見ると、プレミアム会員の詳細と登録方法が載ってるよ〜"
    
    # 使用回数を増加
    user_data["daily_usage_count"] = daily_usage_count + 1
    return True, None

# 褒めメッセージ画像生成機能は archived_features/heart_praise_feature/ に移動しました
# def make_praise_image(praise_text):
#     """褒めメッセージ画像を生成する""" 
#     機能停止: 2025-07-21
#     アーカイブ場所: archived_features/heart_praise_feature/praise_image_function.py

def extract_embed_content(message):
    """メッセージのEmbedから内容を抽出する"""
    try:
        if not message.embeds:
            return None
        
        embed_content = ""
        
        for embed in message.embeds:
            # タイトルを追加
            if embed.title:
                embed_content += f"# {embed.title}\n\n"
            
            # 説明文を追加
            if embed.description:
                embed_content += f"{embed.description}\n\n"
            
            # フィールドを追加
            for field in embed.fields:
                if field.name and field.value:
                    # リンク形式の場合は実際のテキストを抽出
                    field_value = field.value
                    # [テキスト](URL) 形式からテキスト部分を抽出
                    import re
                    link_match = re.search(r'\[([^\]]+)\]\([^)]+\)', field_value)
                    if link_match:
                        field_value = link_match.group(1)
                    
                    embed_content += f"**{field.name}**: {field_value}\n\n"
        
        if embed_content.strip():
            logger.info(f"Embed内容を抽出: {len(embed_content)}文字")
            return embed_content.strip()
        
        return None
        
    except Exception as e:
        logger.error(f"Embed内容抽出エラー: {e}")
        return None

async def read_text_attachment(attachment):
    """添付ファイルからテキスト内容を読み取る"""
    try:
        # テキストファイルの拡張子をチェック
        text_extensions = ['.txt', '.md', '.json', '.csv', '.log', '.py', '.js', '.html', '.css', '.xml']
        file_extension = Path(attachment.filename).suffix.lower()
        
        if file_extension not in text_extensions:
            return None
        
        # ファイルサイズをチェック（1MB以下）
        if attachment.size > 1024 * 1024:
            logger.warning(f"ファイルサイズが大きすぎます: {attachment.filename} ({attachment.size} bytes)")
            return None
        
        # ファイルをダウンロードして内容を読み取り
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as response:
                if response.status == 200:
                    content_bytes = await response.read()
                    # UTF-8で読み取り、失敗したら他のエンコーディングを試す
                    try:
                        content = content_bytes.decode('utf-8')
                        logger.info(f"テキストファイル読み取り成功: {attachment.filename} ({len(content)}文字)")
                        return content
                    except UnicodeDecodeError:
                        try:
                            content = content_bytes.decode('shift_jis')
                            logger.info(f"テキストファイル読み取り成功(Shift-JIS): {attachment.filename} ({len(content)}文字)")
                            return content
                        except UnicodeDecodeError:
                            logger.warning(f"テキストファイルのエンコーディングを判定できませんでした: {attachment.filename}")
                            return None
                else:
                    logger.warning(f"ファイルダウンロードに失敗: {attachment.filename} (status: {response.status})")
                    return None
                    
    except Exception as e:
        logger.error(f"テキストファイル読み取りエラー: {attachment.filename}, {e}")
        return None

def shorten_url(long_url):
    """is.gdを使ってURLを短縮する"""
    try:
        logger.info(f"URL短縮開始 - 元のURL長: {len(long_url)}文字")
        
        # is.gd APIを使用（POSTでリクエスト）
        api_url = "https://is.gd/create.php"
        data = {
            'format': 'simple',
            'url': long_url
        }
        
        response = requests.post(api_url, data=data, timeout=10)
        logger.info(f"is.gd応答ステータス: {response.status_code}")
        
        if response.status_code == 200:
            short_url = response.text.strip()
            # エラーメッセージの場合は失敗扱い
            if short_url.startswith('Error:') or not short_url.startswith('http'):
                logger.warning(f"is.gd短縮失敗 - エラー: {short_url}")
                return long_url  # 短縮失敗時は元のURLを返す
            
            logger.info(f"短縮成功: {short_url}")
            return short_url
        else:
            logger.warning(f"is.gd短縮失敗 - ステータス: {response.status_code}")
            return long_url  # 短縮失敗時は元のURLを返す
    except requests.exceptions.Timeout:
        logger.warning("URL短縮タイムアウト")
        return long_url
    except requests.exceptions.RequestException as e:
        logger.error(f"URL短縮接続エラー: {e}")
        return long_url
    except Exception as e:
        logger.error(f"URL短縮予期しないエラー: {e}")
        return long_url

async def transcribe_audio(message, channel, reaction_user):
    """音声ファイルを文字起こしする"""
    try:
        
        # 音声・動画ファイルを検索
        AUDIO_EXTS = ('.mp3', '.m4a', '.ogg', '.webm', '.wav')
        VIDEO_EXTS = ('.mp4',)
        target_attachment = None
        is_video = False
        
        for attachment in message.attachments:
            filename_lower = attachment.filename.lower()
            if filename_lower.endswith(AUDIO_EXTS):
                target_attachment = attachment
                is_video = False
                break
            elif filename_lower.endswith(VIDEO_EXTS):
                target_attachment = attachment
                is_video = True
                break
        
        if not target_attachment:
            await channel.send("⚠️ 音声・動画ファイルが見つかりません。対応形式: mp3, m4a, ogg, webm, wav, mp4")
            return
        
        # ファイルサイズチェック（音声：100MB、動画：500MB制限）
        if is_video:
            max_size = 500 * 1024 * 1024  # 500MB
            size_text = "500MB"
        else:
            max_size = 100 * 1024 * 1024   # 100MB
            size_text = "100MB"
        
        if target_attachment.size > max_size:
            await channel.send(f"❌ ファイルサイズが{size_text}を超えています。")
            return
        
        # メッセージリンクを作成
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        
        if is_video:
            await channel.send(f"{reaction_user.mention} 🎬 動画から音声を抽出して文字起こしを開始しますね‼️ 少々お待ちください\n📎 元メッセージ: {message_link}")
        else:
            await channel.send(f"{reaction_user.mention} 🎤 音声の文字起こしを開始しますね‼️ 少々お待ちください\n📎 元メッセージ: {message_link}")
        
        # 一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # ファイルをダウンロード
            file_extension = target_attachment.filename.split('.')[-1]
            original_file_path = temp_path / f"original.{file_extension}"
            await target_attachment.save(original_file_path)
            
            logger.info(f"ファイルダウンロード完了: {target_attachment.filename} ({target_attachment.size} bytes)")
            
            # 動画の場合は音声を抽出
            if is_video:
                try:
                    logger.info("動画から音声を抽出中...")
                    video = AudioSegment.from_file(original_file_path)
                    audio_file_path = temp_path / "extracted_audio.mp3"
                    video.export(audio_file_path, format="mp3")
                    logger.info("音声抽出完了")
                except Exception as e:
                    logger.error(f"音声抽出エラー: {e}")
                    await channel.send("❌ 動画から音声の抽出に失敗しました。")
                    return
            else:
                audio_file_path = original_file_path
            
            logger.info(f"処理対象ファイル: {audio_file_path}")
            
            # 音声ファイルを読み込み
            try:
                audio = AudioSegment.from_file(audio_file_path)
            except Exception as e:
                logger.error(f"音声ファイル読み込みエラー: {e}")
                await channel.send("❌ 音声ファイルの読み込みに失敗しました。対応形式か確認してください。")
                return
            
            # 音声の長さを確認し、分割処理を決定
            audio_length_ms = len(audio)
            audio_length_sec = audio_length_ms / 1000
            logger.info(f"音声長: {audio_length_sec:.2f}秒")
            
            # ファイルサイズに基づいて分割数を計算
            # 25MB制限を考慮して安全に20MBを目標とする
            target_size_mb = 20
            
            # 動画の場合は抽出されたMP3のサイズを使用、音声の場合は元ファイルサイズを使用
            if is_video:
                actual_size_mb = audio_file_path.stat().st_size / (1024 * 1024)
                logger.info(f"動画から抽出されたMP3サイズ: {actual_size_mb:.1f}MB")
            else:
                actual_size_mb = target_attachment.size / (1024 * 1024)
                logger.info(f"音声ファイルサイズ: {actual_size_mb:.1f}MB")
            
            time_based_split_count = max(1, int(audio_length_ms // (600 * 1000)))  # 10分基準
            size_based_split_count = max(1, int(actual_size_mb / target_size_mb))  # 実際のサイズ基準
            
            # より大きい分割数を採用（安全のため）
            split_count = max(time_based_split_count, size_based_split_count)
            logger.info(f"時間基準: {time_based_split_count}分割, サイズ基準: {size_based_split_count}分割 → {split_count}分割で処理します")
            
            # 音声ファイルを分割
            parts = []
            part_duration = audio_length_ms // split_count
            
            for i in range(split_count):
                start_time = i * part_duration
                end_time = min((i + 1) * part_duration, audio_length_ms)
                part_audio = audio[start_time:end_time]
                part_file_path = temp_path / f"part_{i}.mp3"
                part_audio.export(part_file_path, format="mp3")
                
                # 分割ファイルのサイズをチェック
                part_size_mb = part_file_path.stat().st_size / (1024 * 1024)
                parts.append(part_file_path)
                logger.info(f"分割ファイル作成: part_{i}.mp3 ({start_time}ms～{end_time}ms, {part_size_mb:.1f}MB)")
            
            # Whisperで各分割ファイルを文字起こし
            logger.info("Whisperによる文字起こし開始")
            full_transcription = ""
            
            for idx, part_file_path in enumerate(parts):
                logger.info(f"{idx+1}/{split_count}: {part_file_path.name} 文字起こし中...")
                
                try:
                    with open(part_file_path, "rb") as audio_file:
                        transcription = client_openai.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="ja"  # 日本語指定
                        )
                        full_transcription += transcription.text + "\n"
                        logger.info(f"パート {idx+1} の文字起こし完了")
                except Exception as api_error:
                    logger.error(f"Whisper API エラー (パート {idx+1}): {api_error}")
                    # タイムアウトエラーの場合は特別なメッセージ
                    if "timeout" in str(api_error).lower() or "timed out" in str(api_error).lower():
                        await channel.send(f"{reaction_user.mention} ⏰ 申し訳ありません！文字起こし処理がタイムアウトしました。\n音声ファイルが大きいか、OpenAI APIが混雑している可能性があります。\n🔄 少し時間をおいてもう一度試してみてください。")
                    else:
                        await channel.send(f"{reaction_user.mention} ❌ 文字起こし処理中にエラーが発生しました。\n🔄 もう一度試してみてください。")
                    return
            
            logger.info(f"文字起こし完了: {len(full_transcription)}文字")
            
            # 文字起こし結果をテキストファイルとして保存
            original_name = os.path.splitext(target_attachment.filename)[0]
            transcript_filename = f"{original_name}_transcript.txt"
            transcript_path = temp_path / transcript_filename
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                if is_video:
                    f.write(f"動画ファイル: {target_attachment.filename}\n")
                else:
                    f.write(f"音声ファイル: {target_attachment.filename}\n")
                f.write(f"音声長: {audio_length_sec:.2f}秒\n")
                f.write(f"処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n\n")
                f.write(full_transcription)
            
            # 結果をDiscordに分割送信（1000文字ずつ）
            await channel.send("🎉 文字起こしが完了したよ〜！")
            await channel.send("-" * 30)
            
            if full_transcription.strip():
                # 1000文字ずつに分割して送信
                for chunk in [full_transcription[j:j+1000] for j in range(0, len(full_transcription), 1000)]:
                    await channel.send(chunk)
                    await asyncio.sleep(1)  # 連続送信を避けるためのウェイト
            else:
                await channel.send("⚠️ 文字起こし結果が空でした。")
            
            await channel.send("-" * 30)
            file_message = await channel.send("📄 文字起こし結果のテキストファイルです！", file=discord.File(transcript_path))
            
            # 文字起こし結果ファイルに自動でリアクションを追加
            reactions = ['👍', '❓', '✏️', '📝']  # ❤️褒めメッセージ機能は停止
            for reaction in reactions:
                try:
                    await file_message.add_reaction(reaction)
                    await asyncio.sleep(0.5)  # Discord API レート制限対策
                except Exception as e:
                    logger.warning(f"リアクション追加エラー ({reaction}): {e}")
            
            logger.info("文字起こし結果ファイルにリアクションを追加しました")
            
    except Exception as e:
        logger.error(f"音声文字起こしエラー: {e}")
        await channel.send("❌ 文字起こし処理中にエラーが発生しました。")

@bot.event
async def on_ready():
    """Bot起動時の処理"""
    print(f'DEBUG: on_ready開始 - {bot.user}', flush=True)
    logger.info(f'Bot起動完了: {bot.user}')
    print(f'DEBUG: logger.info完了', flush=True)
    
    # 登録されているコマンドを確認
    print(f'DEBUG: bot.tree.get_commands()実行前', flush=True)
    try:
        commands = bot.tree.get_commands()
        print(f'DEBUG: get_commands()成功 - コマンド数: {len(commands)}', flush=True)
        print(f"登録されているコマンド数: {len(commands)}")
    except Exception as e:
        print(f'DEBUG: get_commands()でエラー: {e}', flush=True)
    
    print(f'DEBUG: コマンド詳細表示開始', flush=True)
    try:
        for i, cmd in enumerate(bot.tree.get_commands()):
            print(f'DEBUG: コマンド{i+1}: {cmd.name}', flush=True)
            print(f"- {cmd.name}: {cmd.description}")
    except Exception as e:
        print(f'DEBUG: コマンド詳細表示でエラー: {e}', flush=True)
    
    # スラッシュコマンドを強制的に書き換え
    try:
        print("DEBUG: スラッシュコマンド同期処理開始")
        test_guild = discord.Object(id=TEST_GUILD_ID)
        print(f"DEBUG: test_guild作成完了 ID={TEST_GUILD_ID}")
        
        # Step 1: 既存のギルドコマンドを完全にクリア
        print("=== 既存コマンドのクリア処理開始 ===")
        print("DEBUG: clear_commands実行前")
        bot.tree.clear_commands(guild=test_guild)
        print("DEBUG: clear_commands実行完了、sync実行開始")
        empty_sync = await bot.tree.sync(guild=test_guild)
        print("DEBUG: sync実行完了")
        print(f"テストサーバーのコマンドをクリア完了: {len(empty_sync)} 個")
        
        # Step 2: 新しいコマンドを追加
        print("=== 新しいコマンドの追加処理開始 ===")
        synced_guild = await bot.tree.sync(guild=test_guild)
        print(f'テストサーバー ({TEST_GUILD_ID}) に {len(synced_guild)} 個のスラッシュコマンドを強制同期しました')
        for cmd in synced_guild:
            print(f"  ✅ {cmd['name']}: {cmd.get('description', 'N/A')}")
        
        # Step 3: グローバルにも同期
        print("=== グローバル同期処理開始 ===")
        synced_global = await bot.tree.sync()
        print(f'グローバルに {len(synced_global)} 個のスラッシュコマンドを同期しました')
        
        print("=== コマンド同期処理完了 ===")
        
    except Exception as e:
        logger.error(f'❌ スラッシュコマンドの同期に失敗しました: {e}')
        import traceback
        logger.error(traceback.format_exc())

@bot.tree.command(name="help", description="利用可能なコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    """ヘルプコマンド"""
    embed = discord.Embed(
        title="🤖 Bot コマンド一覧",
        description="利用可能なコマンド:",
        color=0x00ff00
    )
    
    embed.add_field(
        name="/help", 
        value="このヘルプメッセージを表示", 
        inline=False
    )
    embed.add_field(
        name="/activate", 
        value="このチャンネルでBotを有効化（管理者のみ）", 
        inline=False
    )
    embed.add_field(
        name="/deactivate", 
        value="このチャンネルでBotを無効化（管理者のみ）", 
        inline=False
    )
    embed.add_field(
        name="/status", 
        value="サーバー内の有効チャンネル一覧を表示（管理者のみ）", 
        inline=False
    )
    embed.add_field(
        name="/set_custom_prompt_x_post", 
        value="X投稿用のカスタムプロンプトを設定（空白入力で無効化）", 
        inline=False
    )
    embed.add_field(
        name="/set_custom_prompt_article", 
        value="記事作成用のカスタムプロンプトを設定（空白入力で無効化）", 
        inline=False
    )
    embed.add_field(
        name="/set_custom_prompt_memo", 
        value="メモ作成用のカスタムプロンプトを設定（空白入力で無効化）", 
        inline=False
    )
    embed.add_field(
        name="/set_custom_prompt_summary", 
        value="記事要約用のカスタムプロンプトを設定（空白入力で無効化）", 
        inline=False
    )
    
    # リアクション機能の説明を追加
    embed.add_field(
        name="📢 リアクション機能", 
        value=(
            "👍 **X投稿生成** - メッセージ・ファイルをX用に要約\n"
            "🎤 **音声文字起こし** - 音声・動画ファイルをテキストに変換\n"
            "❓ **AI解説** - 内容について詳しく解説\n"
            "✏️ **メモ作成** - Obsidian用Markdownメモ生成\n"
            "📝 **記事作成** - PREP法に基づく構造化記事生成\n"
            "🌐 **URL取得** - URLからコンテンツを取得してテキストファイル化\n"
            "🙌 **記事要約** - URLの記事を3行で要約（キーフレーズ付き）\n"
            "👀 **Xツリー投稿** - メッセージからエンゲージメント重視のXツリー投稿生成（AI画像付き）"
        ), 
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# カスタムプロンプト設定用のModalクラス
class CustomPromptModal(discord.ui.Modal, title='X投稿用カスタムプロンプト設定'):
    def __init__(self, current_prompt=""):
        super().__init__()
        # テキスト入力エリア（複数行対応）
        self.prompt_input = discord.ui.TextInput(
            label='カスタムプロンプト',
            placeholder='X投稿生成用のプロンプトを入力してください...\n改行も使用できます。\n\n※ 空のまま送信するとカスタムプロンプトが無効になり、デフォルトプロンプトが使用されます。',
            style=discord.TextStyle.paragraph,  # 複数行入力
            max_length=2000,
            required=False,
            default=current_prompt  # 既存の値をプリフィル
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt = self.prompt_input.value.strip()  # 前後の空白を削除
            
            # ユーザーデータを読み込み（存在しない場合は新規作成）
            user_id = interaction.user.id
            user_data = load_user_data(user_id)
            if user_data is None:
                user_data = {
                    "custom_prompt_x_post": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
            
            # カスタムプロンプトを更新
            user_data["custom_prompt_x_post"] = prompt
            
            # ユーザーデータを保存
            save_user_data(user_id, user_data)
            
            # 設定内容に応じてメッセージを変更
            if prompt:
                print(f"ユーザー {interaction.user.name} ({user_id}) がカスタムプロンプトを設定しました")
                print(f"プロンプト内容: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
                await interaction.response.send_message("✅ カスタムプロンプトを設定しました！", ephemeral=True)
            else:
                print(f"ユーザー {interaction.user.name} ({user_id}) がカスタムプロンプトを無効化しました")
                await interaction.response.send_message("✅ カスタムプロンプトを無効化しました。デフォルトプロンプトを使用します。", ephemeral=True)
            
        except Exception as e:
            logger.error(f"カスタムプロンプト設定エラー: {e}")
            await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.error(f"Modal エラー: {error}")
        await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

@bot.tree.command(name="set_custom_prompt_x_post", description="X投稿用のカスタムプロンプトを設定します")
async def set_custom_prompt_x_post_command(interaction: discord.Interaction):
    """カスタムプロンプト設定コマンド"""
    # 既存のユーザーデータを読み込み
    user_id = interaction.user.id
    user_data = load_user_data(user_id)
    current_prompt = ""
    if user_data and "custom_prompt_x_post" in user_data:
        current_prompt = user_data["custom_prompt_x_post"]
    
    modal = CustomPromptModal(current_prompt)
    await interaction.response.send_modal(modal)

# 記事作成用カスタムプロンプト設定のModalクラス
class CustomArticlePromptModal(discord.ui.Modal, title='記事作成用カスタムプロンプト設定'):
    def __init__(self, current_prompt=""):
        super().__init__()
        # テキスト入力エリア（複数行対応）
        self.prompt_input = discord.ui.TextInput(
            label='カスタムプロンプト',
            placeholder='記事作成用のプロンプトを入力してください...\n改行も使用できます。\n\n※ 空のまま送信するとカスタムプロンプトが無効になり、デフォルトプロンプトが使用されます。',
            style=discord.TextStyle.paragraph,  # 複数行入力
            max_length=2000,
            required=False,
            default=current_prompt  # 既存の値をプリフィル
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt = self.prompt_input.value.strip()  # 前後の空白を削除
            
            # ユーザーデータを読み込み（存在しない場合は新規作成）
            user_id = interaction.user.id
            user_data = load_user_data(user_id)
            if user_data is None:
                user_data = {
                    "custom_prompt_x_post": "",
                    "custom_prompt_article": "",
                    "custom_prompt_memo": "",
                    "custom_prompt_summary": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
            
            # 記事用カスタムプロンプトを更新
            user_data["custom_prompt_article"] = prompt
            
            # ユーザーデータを保存
            save_user_data(user_id, user_data)
            
            # 設定内容に応じてメッセージを変更
            if prompt:
                print(f"ユーザー {interaction.user.name} ({user_id}) が記事用カスタムプロンプトを設定しました")
                print(f"プロンプト内容: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
                await interaction.response.send_message("✅ 記事作成用カスタムプロンプトを設定しました！", ephemeral=True)
            else:
                print(f"ユーザー {interaction.user.name} ({user_id}) が記事用カスタムプロンプトを無効化しました")
                await interaction.response.send_message("✅ 記事作成用カスタムプロンプトを無効化しました。デフォルトプロンプトを使用します。", ephemeral=True)
            
        except Exception as e:
            logger.error(f"記事用カスタムプロンプト設定エラー: {e}")
            await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.error(f"Modal エラー: {error}")
        await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

@bot.tree.command(name="set_custom_prompt_article", description="記事作成用のカスタムプロンプトを設定します")
async def set_custom_prompt_article_command(interaction: discord.Interaction):
    """記事用カスタムプロンプト設定コマンド"""
    # 既存のユーザーデータを読み込み
    user_id = interaction.user.id
    user_data = load_user_data(user_id)
    current_prompt = ""
    if user_data and "custom_prompt_article" in user_data:
        current_prompt = user_data["custom_prompt_article"]
    
    modal = CustomArticlePromptModal(current_prompt)
    await interaction.response.send_modal(modal)

# メモ作成用カスタムプロンプト設定のModalクラス
class CustomMemoPromptModal(discord.ui.Modal, title='メモ作成用カスタムプロンプト設定'):
    def __init__(self, current_prompt=None):
        super().__init__()
        
        # テキスト入力エリア（複数行対応）
        self.prompt_input = discord.ui.TextInput(
            label='カスタムプロンプト',
            placeholder='メモ作成用のプロンプトを入力してください...\n改行も使用できます。\n\n※ 空のまま送信するとカスタムプロンプトが無効になり、デフォルトプロンプトが使用されます。',
            style=discord.TextStyle.paragraph,  # 複数行入力
            max_length=2000,
            required=False,
            default=current_prompt if current_prompt else ''
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt = self.prompt_input.value.strip()  # 前後の空白を削除
            
            # ユーザーデータを読み込み（存在しない場合は新規作成）
            user_id = interaction.user.id
            user_data = load_user_data(user_id)
            if user_data is None:
                user_data = {
                    "custom_prompt_x_post": "",
                    "custom_prompt_article": "",
                    "custom_prompt_memo": "",
                    "custom_prompt_summary": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
            
            # メモ用カスタムプロンプトを更新
            user_data["custom_prompt_memo"] = prompt
            
            # ユーザーデータを保存
            save_user_data(user_id, user_data)
            
            # 設定内容に応じてメッセージを変更
            if prompt:
                print(f"ユーザー {interaction.user.name} ({user_id}) がメモ用カスタムプロンプトを設定しました")
                print(f"プロンプト内容: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
                await interaction.response.send_message("✅ メモ作成用カスタムプロンプトを設定しました！", ephemeral=True)
            else:
                print(f"ユーザー {interaction.user.name} ({user_id}) がメモ用カスタムプロンプトを無効化しました")
                await interaction.response.send_message("✅ メモ作成用カスタムプロンプトを無効化しました。デフォルトプロンプトを使用します。", ephemeral=True)
            
        except Exception as e:
            logger.error(f"メモ用カスタムプロンプト設定エラー: {e}")
            await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.error(f"Modal エラー: {error}")
        await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

class CustomSummaryPromptModal(discord.ui.Modal, title='要約用カスタムプロンプト設定'):
    def __init__(self, current_prompt=None):
        super().__init__()
        
        # テキスト入力エリア（複数行対応）
        self.prompt_input = discord.ui.TextInput(
            label='カスタムプロンプト',
            placeholder='記事要約用のプロンプトを入力してください...\n改行も使用できます。\n\n※ 空のまま送信するとカスタムプロンプトが無効になり、デフォルトプロンプトが使用されます。',
            style=discord.TextStyle.paragraph,  # 複数行入力
            max_length=2000,
            required=False,
            default=current_prompt if current_prompt else ''
        )
        self.add_item(self.prompt_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt = self.prompt_input.value.strip()  # 前後の空白を削除
            
            # ユーザーデータを読み込み（存在しない場合は新規作成）
            user_id = interaction.user.id
            user_data = load_user_data(user_id)
            if user_data is None:
                user_data = {
                    "custom_prompt_x_post": "",
                    "custom_prompt_article": "",
                    "custom_prompt_memo": "",
                    "custom_prompt_summary": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
            
            user_data["custom_prompt_summary"] = prompt
            save_user_data(user_id, user_data)
            
            if prompt:
                await interaction.response.send_message(f"✅ 要約用カスタムプロンプトを設定しました！\n\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```", ephemeral=True)
                logger.info(f"ユーザー {interaction.user.name} ({user_id}) が要約用カスタムプロンプトを設定しました")
            else:
                await interaction.response.send_message("✅ 要約用カスタムプロンプトを無効にしました。デフォルトプロンプトが使用されます。", ephemeral=True)
                logger.info(f"ユーザー {interaction.user.name} ({user_id}) が要約用カスタムプロンプトを無効にしました")
            
        except Exception as e:
            logger.error(f"要約用カスタムプロンプト設定エラー: {e}")
            await interaction.response.send_message("❌ プロンプトの設定中にエラーが発生しました。", ephemeral=True)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.error(f"Modal エラー: {error}")
        await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

@bot.tree.command(name="set_custom_prompt_memo", description="メモ作成用のカスタムプロンプトを設定します")
async def set_custom_prompt_memo_command(interaction: discord.Interaction):
    """メモ用カスタムプロンプト設定コマンド"""
    # 既存のユーザーデータを読み込み
    user_id = interaction.user.id
    user_data = load_user_data(user_id)
    current_prompt = ""
    if user_data and "custom_prompt_memo" in user_data:
        current_prompt = user_data["custom_prompt_memo"]
    
    modal = CustomMemoPromptModal(current_prompt)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="set_custom_prompt_summary", description="要約機能用のカスタムプロンプトを設定します")
async def set_custom_prompt_summary_command(interaction: discord.Interaction):
    """要約用カスタムプロンプト設定コマンド"""
    # 既存のユーザーデータを読み込み
    user_id = interaction.user.id
    user_data = load_user_data(user_id)
    current_prompt = ""
    if user_data and "custom_prompt_summary" in user_data:
        current_prompt = user_data["custom_prompt_summary"]
    
    modal = CustomSummaryPromptModal(current_prompt)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="activate", description="このチャンネルでBotを有効化します")
async def activate_command(interaction: discord.Interaction):
    """アクティベートコマンド"""
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)
    
    # サーバーデータを読み込み
    server_data = load_server_data(server_id)
    if server_data is None:
        server_data = {
            "server_id": server_id,
            "server_name": interaction.guild.name,
            "active_channel_ids": []
        }
    
    # server_nameを更新（サーバー名が変更された場合に対応）
    server_data['server_name'] = interaction.guild.name
    
    # チャンネルIDを追加
    if channel_id not in server_data['active_channel_ids']:
        server_data['active_channel_ids'].append(channel_id)
        save_server_data(server_id, server_data)
        
        # 使い方ガイドメッセージを作成
        guide_message = (
            f"✅ このチャンネル（{interaction.channel.name}）でBotを有効化しました！\n\n"
            "**📖 使い方**\n"
            "メッセージに以下のリアクションを付けると、それぞれの機能が動作します：\n\n"
            "👍 **X投稿生成** - メッセージをX（旧Twitter）投稿用に最適化\n"
            "🎤 **音声文字起こし** - 音声ファイルをテキストに変換\n"
            "❓ **AI解説** - メッセージ内容を詳しく解説\n"
# "❤️ **褒めメッセージ** - 熱烈な応援メッセージと画像を生成\n"  # 機能停止
            "✏️ **メモ作成** - Obsidian用のMarkdownメモを自動生成\n"
            "📝 **記事作成** - 記事を作成（カスタムプロンプト対応）\n\n"
            "👇試しに下のリアクションを押してみて👇"
        )
        
        await interaction.response.send_message(guide_message)
        
        # 送信したメッセージを取得してリアクションを追加
        message = await interaction.original_response()
        reactions = ['👍', '❓', '✏️', '📝']  # ❤️褒めメッセージ機能は停止
        for emoji in reactions:
            await message.add_reaction(emoji)
            await asyncio.sleep(0.5)  # リアクション追加の間隔を空ける
        
        # サンプル音声ファイルを送信
        sample_audio_path = script_dir / "audio" / "sample_voice.mp3"
        if sample_audio_path.exists():
            try:
                audio_message = await interaction.followup.send(
                    "🎵 試しに音声文字起こし機能を使ってみてください！",
                    file=discord.File(sample_audio_path)
                )
                # サンプル音声にマイクリアクションを追加
                await audio_message.add_reaction('🎤')
                logger.info("サンプル音声ファイル送信完了")
            except Exception as e:
                logger.error(f"サンプル音声ファイル送信エラー: {e}")
        else:
            logger.warning(f"サンプル音声ファイルが見つかりません: {sample_audio_path}")
    else:
        await interaction.response.send_message(f"ℹ️ このチャンネル（{interaction.channel.name}）は既に有効です。")

@bot.tree.command(name="deactivate", description="このチャンネルでBotを無効化します")
async def deactivate_command(interaction: discord.Interaction):
    """ディアクティベートコマンド"""
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)
    
    # サーバーデータを読み込み
    server_data = load_server_data(server_id)
    if server_data is None:
        await interaction.response.send_message("❌ サーバーデータが見つかりません。")
        return
    
    # チャンネルIDを削除
    if channel_id in server_data['active_channel_ids']:
        server_data['active_channel_ids'].remove(channel_id)
        save_server_data(server_id, server_data)
        await interaction.response.send_message(f"✅ このチャンネル（{interaction.channel.name}）でBotを無効化しました。")
    else:
        await interaction.response.send_message(f"ℹ️ このチャンネル（{interaction.channel.name}）は既に無効です。")

@bot.tree.command(name="status", description="サーバー内の有効チャンネル一覧を表示します")
async def status_command(interaction: discord.Interaction):
    """ステータスコマンド"""
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    server_data = load_server_data(server_id)
    
    if server_data and "active_channel_ids" in server_data:
        channel_list = []
        for channel_id in server_data["active_channel_ids"]:
            channel = bot.get_channel(int(channel_id))
            if channel:
                channel_list.append(f"• {channel.name}")
            else:
                channel_list.append(f"• ID: {channel_id} (チャンネルが見つかりません)")
        
        if channel_list:
            channel_text = "\n".join(channel_list)
        else:
            channel_text = "有効なチャンネルがありません"
    else:
        channel_text = "有効なチャンネルがありません"
    
    embed = discord.Embed(
        title="📋 有効チャンネル一覧",
        description=channel_text,
        color=0x00ff00
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stats", description="Bot統計情報を表示します")
async def stats_command(interaction: discord.Interaction):
    """統計コマンド（オーナー専用）"""
    # オーナー権限チェック
    user_id = str(interaction.user.id)
    
    # settings.jsonからowner_user_idを取得
    settings_path = script_dir / "settings.json"
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            owner_user_id = settings.get("owner_user_id")
    else:
        owner_user_id = None
    
    # オーナーかどうかチェック
    if not owner_user_id or user_id != str(owner_user_id):
        await interaction.response.send_message("❌ このコマンドはオーナーのみ使用できます。", ephemeral=True)
        return
    
    try:
        # 統計を計算
        stats = stats_manager.get_stats_summary()
        server_count = len(bot.guilds)
        
        embed = discord.Embed(
            title="📊 Bot統計情報",
            color=0x00ff00
        )
        
        embed.add_field(name="📅 集計日", value=stats["date"], inline=True)
        embed.add_field(name="🏠 現在のサーバー数", value=f"{server_count:,}", inline=True)
        embed.add_field(name="🏠 記録時サーバー数", value=f"{stats['server_count']:,}", inline=True)
        embed.add_field(name="📈 DAU", value=f"{stats['dau']:,}", inline=True)
        embed.add_field(name="📊 MAU", value=f"{stats['mau']:,}", inline=True)
        embed.add_field(name="⚡ 今日のアクション数", value=f"{stats['total_actions_today']:,}", inline=True)
        embed.add_field(name="🕐 更新時刻", value=datetime.now().strftime("%H:%M:%S"), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"統計コマンドエラー: {e}")
        await interaction.response.send_message("❌ 統計取得中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="restart", description="Botを再起動します（オーナー専用）")
async def restart_command(interaction: discord.Interaction):
    """Botリスタートコマンド（オーナー専用）"""
    # オーナー権限チェック
    user_id = str(interaction.user.id)
    
    # settings.jsonからowner_user_idを取得
    settings_path = script_dir / "settings.json"
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            owner_user_id = settings.get("owner_user_id")
    else:
        owner_user_id = None
    
    # オーナーかどうかチェック
    if not owner_user_id or user_id != str(owner_user_id):
        await interaction.response.send_message("❌ このコマンドはオーナーのみ使用できます。", ephemeral=True)
        return
    
    try:
        # 再起動メッセージを送信
        await interaction.response.send_message("🔄 Botを再起動しています...", ephemeral=True)
        
        # ログに記録
        logger.info(f"Bot再起動要求 - ユーザー: {interaction.user.name} ({user_id})")
        
        # Bot終了（プロセスマネージャーがあれば自動再起動、なければ手動再起動が必要）
        await bot.close()
        
    except Exception as e:
        logger.error(f"再起動コマンドエラー: {e}")
        await interaction.followup.send("❌ 再起動中にエラーが発生しました。", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    """リアクション追加時の処理"""
    # Botのリアクションは無視
    if payload.user_id == bot.user.id:
        return
    
    # リアクションの種類をチェック
    if payload.emoji.name in ['👍', '🎤', '❓', '✏️', '📝', '🌐', '🙌', '👀']:  # 👀ツリー投稿機能追加
        server_id = str(payload.guild_id)
        channel_id = str(payload.channel_id)
        
        # チャンネルが有効かチェック
        if is_channel_active(server_id, channel_id):
            # チャンネルとメッセージを取得
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await bot.fetch_user(payload.user_id)
            
            # 統計記録（ユーザーアクティビティ）
            await stats_manager.record_user_activity(str(payload.user_id), bot)
            
            logger.info(f"{payload.emoji.name} リアクションを検知しました！")
            logger.info(f"サーバー: {message.guild.name}")
            logger.info(f"チャンネル: {channel.name}")
            logger.info(f"ユーザー: {user.name if user else '不明'}")
            logger.info(f"メッセージ: {message.content if message.content else '(空のメッセージ)'}")
            logger.info("-" * 50)
            
            # 共通ユーザーデータ処理
            user_data = load_user_data(user.id)
            if user_data is None:
                # 新規ユーザー
                user_data = {
                    "user_id": str(user.id),
                    "username": user.name,
                    "custom_prompt_x_post": "",
                    "custom_prompt_article": "",
                    "custom_prompt_memo": "",
                    "custom_prompt_summary": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
                save_user_data(user.id, user_data)
                logger.info(f"新規ユーザー {user.name} ({user.id}) のデータを作成しました")
            else:
                # 既存ユーザーのマイグレーション
                user_data, migration_needed = migrate_user_data(user_data, user.id, user.name)
                if migration_needed:
                    save_user_data(user.id, user_data)
                    logger.info(f"ユーザー {user.name} ({user.id}) のデータをマイグレーションしました")
            
            # プレミアム状態確認
            is_premium = await is_premium_user(user.id)
            
            # ユーザー情報とstatusを更新
            user_data["user_id"] = str(user.id)
            user_data["username"] = user.name
            user_data["status"] = "premium" if is_premium else "free"
            
            # 使用制限チェック
            can_use, limit_message = can_use_feature(user_data, is_premium)
            if not can_use:
                await channel.send(f"{user.mention} {limit_message}")
                return
            
            # 使用回数更新
            save_user_data(user.id, user_data)
            
            
            # 👍 サムズアップ：X投稿要約
            if payload.emoji.name == '👍':
                # メッセージ内容または添付ファイル、Embedからテキストを取得
                input_text = message.content
                
                # Embedがある場合は内容を抽出
                embed_content = extract_embed_content(message)
                if embed_content:
                    if input_text:
                        input_text += f"\n\n【Embed内容】\n{embed_content}"
                    else:
                        input_text = embed_content
                    logger.info("Embed内容を追加")
                
                # 添付ファイルがある場合、テキストファイルの内容を読み取り
                if message.attachments:
                    for attachment in message.attachments:
                        file_content = await read_text_attachment(attachment)
                        if file_content:
                            if input_text:
                                input_text += f"\n\n【ファイル: {attachment.filename}】\n{file_content}"
                            else:
                                input_text = f"【ファイル: {attachment.filename}】\n{file_content}"
                            logger.info(f"添付ファイルの内容を追加: {attachment.filename}")
                
                if input_text:
                    # URL検出・警告
                    await check_content_for_urls(input_text, user, channel)
                    
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # 処理開始メッセージを送信
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} X用の投稿を作ってあげるね〜！ちょっと待っててね\n📎 元メッセージ: {message_link}")
                    
                    # X投稿用プロンプトを読み込み（カスタムプロンプトを優先）
                    x_prompt = None
                    
                    # 1. ユーザーのカスタムプロンプトをチェック
                    if user_data and user_data.get('custom_prompt_x_post'):
                        x_prompt = user_data['custom_prompt_x_post']
                        logger.info(f"ユーザー {user.name} のカスタムプロンプトを使用")
                    
                    # 2. カスタムプロンプトがない場合はデフォルトプロンプトファイルを使用
                    if not x_prompt:
                        prompt_path = script_dir / "prompt" / "x_post.txt"
                        if prompt_path.exists():
                            with open(prompt_path, 'r', encoding='utf-8') as f:
                                x_prompt = f.read()
                            logger.info("デフォルトプロンプトファイルを使用")
                        else:
                            x_prompt = "あなたはDiscordの投稿をX（旧Twitter）用に要約するアシスタントです。140文字以内で簡潔に要約してください。"
                            logger.info("フォールバックプロンプトを使用")
                    
                    # プロンプトにJSON出力指示と文字数制限を追加
                    x_prompt += "\n\n出力は以下のJSON形式で返してください：\n{\"content\": \"X投稿用のテキスト\"}\n\n重要な文字数制限：\n- プロンプトで300文字以下の文字数指定がある場合はその文字数に従ってください\n- プロンプトで300文字を超える文字数指定がある場合や指定がない場合は、必ず300文字以内で出力してください\n- 絶対に300文字を超えないでください"
                    
                    # OpenAI APIで要約を生成
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": x_prompt},
                                    {"role": "user", "content": input_text}
                                ],
                                max_tokens=1000,
                                temperature=0.9,
                                response_format={"type": "json_object"}
                            )
                            
                            # JSONレスポンスをパース
                            response_content = response.choices[0].message.content
                            try:
                                response_json = json.loads(response_content)
                                summary = response_json.get("content", response_content)
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析エラー、生のレスポンスを使用: {response_content}")
                                summary = response_content
                            
                            # X投稿用のURLを生成
                            import urllib.parse
                            x_intent_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(summary)}"
                            
                            # URLを短縮
                            shortened_url = shorten_url(x_intent_url)
                            
                            # 結果を送信（Discord制限に合わせて文字数制限）
                            # embed descriptionは4096文字制限、fieldは1024文字制限
                            display_summary = summary[:4000] + "..." if len(summary) > 4000 else summary
                            
                            embed = discord.Embed(
                                title="📝 X投稿用要約",
                                description=display_summary,
                                color=0x1DA1F2
                            )
                            
                            embed.add_field(
                                name="X投稿リンク👇",
                                value=f"[クリックして投稿]({shortened_url})",
                                inline=False
                            )
                            
                            # 完了メッセージと結果を送信
                            await channel.send("🎉 できたよ〜！Xに投稿する場合は下のリンクをクリックしてね！")
                            await channel.send(embed=embed)
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー: {e}")
                            await channel.send(f"{user.mention} ❌ 要約の生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send(f"{user.mention} ❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send(f"{user.mention} ⚠️ **X投稿を作成するためにはテキストが必要です**\n\n"
                                     f"以下のいずれかを行ってから👍リアクションしてください：\n"
                                     f"• テキストメッセージを投稿する\n"
                                     f"• テキストファイル（.txt）を添付する\n"
                                     f"• 音声ファイルの場合は🎤で文字起こしをしてからそのファイルに👍する\n\n"
                                     f"音声ファイルのみでは直接X投稿は作成できません。")
            
            # 🎤 マイク：音声・動画文字起こし
            elif payload.emoji.name == '🎤':
                # 音声・動画ファイルがあるかチェック
                if message.attachments:
                    await transcribe_audio(message, channel, user)
                else:
                    await channel.send(f"{user.mention} ⚠️ **🎤は音声・動画の文字起こし専用です**\n\n"
                                     f"音声ファイル（mp3、wav、m4a等）または動画ファイル（mp4、mov等）が添付されたメッセージにリアクションしてください。\n\n"
                                     f"テキストのみのメッセージには🎤ではなく、以下のリアクションをお使いください：\n"
                                     f"• 👍 X投稿作成\n"
                                     f"• ❓ AI解説\n"
                                     f"• ✏️ 記事作成")
            
            # ❤️ ハート機能：削除済み（archived_features/heart_praise_feature/ に移行済み）
            
            # ❓ 疑問符：AI説明
            elif payload.emoji.name == '❓':
                # メッセージ内容または添付ファイル、Embedからテキストを取得
                input_text = message.content
                
                # Embedがある場合は内容を抽出
                embed_content = extract_embed_content(message)
                if embed_content:
                    if input_text:
                        input_text += f"\n\n【Embed内容】\n{embed_content}"
                    else:
                        input_text = embed_content
                    logger.info("Embed内容を追加")
                
                # 添付ファイルがある場合、テキストファイルの内容を読み取り
                if message.attachments:
                    for attachment in message.attachments:
                        file_content = await read_text_attachment(attachment)
                        if file_content:
                            if input_text:
                                input_text += f"\n\n【ファイル: {attachment.filename}】\n{file_content}"
                            else:
                                input_text = f"【ファイル: {attachment.filename}】\n{file_content}"
                            logger.info(f"添付ファイルの内容を追加: {attachment.filename}")
                
                if input_text:
                    # URL検出・警告
                    await check_content_for_urls(input_text, user, channel)
                    
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # 処理開始メッセージを送信
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} 🤔 投稿内容について詳しく解説するね〜！ちょっと待っててね\n📎 元メッセージ: {message_link}")
                    
                    # 解説用プロンプトを読み込み
                    explain_prompt = None
                    prompt_path = script_dir / "prompt" / "question_explain.txt"
                    if prompt_path.exists():
                        with open(prompt_path, 'r', encoding='utf-8') as f:
                            explain_prompt = f.read()
                        logger.info("解説プロンプトファイルを使用")
                    else:
                        explain_prompt = "あなたはDiscordメッセージの内容について詳しく解説するアシスタントです。投稿内容をわかりやすく、丁寧に解説してください。専門用語があれば説明し、背景情報も補足してください。"
                        logger.info("フォールバック解説プロンプトを使用")
                    
                    # OpenAI APIで解説を生成
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": explain_prompt},
                                    {"role": "user", "content": input_text}
                                ],
                                max_tokens=2000,
                                temperature=0.7
                            )
                            
                            explanation = response.choices[0].message.content
                            
                            # Discord文字数制限対応（2000文字以内に調整）
                            if len(explanation) > 1900:
                                explanation = explanation[:1900] + "..."
                            
                            # 結果を送信
                            embed = discord.Embed(
                                title="🤔 AI解説",
                                description=explanation,
                                color=0xFF6B35
                            )
                            
                            # 元の投稿内容も表示（短縮版）
                            original_content = message.content[:200] + "..." if len(message.content) > 200 else message.content
                            embed.add_field(
                                name="📝 元の投稿",
                                value=original_content,
                                inline=False
                            )
                            
                            await channel.send("💡 解説が完了したよ〜！")
                            await channel.send(embed=embed)
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー (解説機能): {e}")
                            await channel.send(f"{user.mention} ❌ 解説の生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send(f"{user.mention} ❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send(f"{user.mention} ⚠️ メッセージに内容がありません。")
            
            # ✏️ 鉛筆：Obsidianメモ作成
            elif payload.emoji.name == '✏️':
                # メッセージ内容または添付ファイル、Embedからテキストを取得
                input_text = message.content
                
                # Embedがある場合は内容を抽出
                embed_content = extract_embed_content(message)
                if embed_content:
                    if input_text:
                        input_text += f"\n\n【Embed内容】\n{embed_content}"
                    else:
                        input_text = embed_content
                    logger.info("Embed内容を追加")
                
                # 添付ファイルがある場合、テキストファイルの内容を読み取り
                if message.attachments:
                    for attachment in message.attachments:
                        file_content = await read_text_attachment(attachment)
                        if file_content:
                            if input_text:
                                input_text += f"\n\n【ファイル: {attachment.filename}】\n{file_content}"
                            else:
                                input_text = f"【ファイル: {attachment.filename}】\n{file_content}"
                            logger.info(f"添付ファイルの内容を追加: {attachment.filename}")
                
                if input_text:
                    # URL検出・警告
                    await check_content_for_urls(input_text, user, channel)
                    
                    # 処理開始メッセージ
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} 📝 メモを作るよ〜！ちょっと待っててね\n📎 元メッセージ: {message_link}")
                    
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # メモ用プロンプトを読み込み
                    memo_prompt = None
                    
                    # 1. ユーザーのカスタムプロンプトをチェック
                    if user_data and user_data.get('custom_prompt_memo'):
                        memo_prompt = user_data['custom_prompt_memo']
                        logger.info(f"ユーザー {user.name} のメモ用カスタムプロンプトを使用")
                    
                    # 2. カスタムプロンプトがない場合はデフォルトプロンプトファイルを使用
                    if not memo_prompt:
                        prompt_path = script_dir / "prompt" / "pencil_memo.txt"
                        if prompt_path.exists():
                            with open(prompt_path, 'r', encoding='utf-8') as f:
                                memo_prompt = f.read()
                            logger.info("デフォルトメモプロンプトファイルを使用")
                        else:
                            memo_prompt = "あなたはDiscordメッセージの内容をObsidianメモとして整理するアシスタントです。内容に忠実にメモ化してください。追加情報は加えず、原文を尊重してください。客観的にみて不要と思われる情報は削除して構いません。"
                            logger.info("フォールバックメモプロンプトを使用")
                    
                    # プロンプトにJSON出力指示を追加（カスタムプロンプトでも対応）
                    json_instruction = '\n\n出力はJSON形式で、以下のフォーマットに従ってください：\n{"english_title": "english_title_for_filename", "content": "メモの内容"}'
                    memo_prompt += json_instruction
                    
                    # OpenAI APIでメモを生成（JSONモード）
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": memo_prompt},
                                    {"role": "user", "content": input_text}
                                ],
                                max_tokens=2000,
                                temperature=0.3,
                                response_format={"type": "json_object"}
                            )
                            
                            # JSONレスポンスをパース
                            response_content = response.choices[0].message.content
                            try:
                                memo_json = json.loads(response_content)
                                english_title = memo_json.get("english_title", "untitled_memo")
                                content = memo_json.get("content", input_text)
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析エラー、フォールバックを使用: {response_content}")
                                english_title = "untitled_memo"
                                content = input_text
                            
                            # ファイル名を生成（YYYYMMDD_HHMMSS_english_title.md）
                            now = datetime.now()
                            timestamp = now.strftime("%Y%m%d_%H%M%S")
                            # 英語タイトルを安全なファイル名に変換
                            safe_english_title = re.sub(r'[^A-Za-z0-9\-_]', '', english_title)
                            if not safe_english_title:
                                safe_english_title = "memo"
                            filename = f"{timestamp}_{safe_english_title}.md"
                            
                            # attachmentsフォルダにファイルを保存
                            attachments_dir = script_dir / "attachments"
                            attachments_dir.mkdir(exist_ok=True)
                            file_path = attachments_dir / filename
                            
                            # ファイル内容：コンテンツをそのまま保存
                            file_content = content
                            
                            # UTF-8でファイル保存
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(file_content)
                            
                            logger.info(f"メモファイル作成: {file_path}")
                            
                            try:
                                # 結果を送信
                                embed = discord.Embed(
                                    title="📝 Obsidianメモを作成しました",
                                    description=f"**ファイル名**: `{filename}`",
                                    color=0x7C3AED
                                )
                                
                                # 内容のプレビュー（最初の200文字）
                                preview = content[:200] + "..." if len(content) > 200 else content
                                embed.add_field(
                                    name="📄 内容プレビュー",
                                    value=preview,
                                    inline=False
                                )
                                
                                await channel.send(embed=embed)
                                
                                # ファイルをアップロード
                                with open(file_path, 'rb') as f:
                                    file_data = f.read()
                                
                                file_obj = io.BytesIO(file_data)
                                file_message = await channel.send("📝 メモファイルを作成しました！", file=discord.File(file_obj, filename=filename))
                                
                                # メモファイルに自動でリアクションを追加
                                reactions = ['👍', '❓', '✏️', '📝']  # ❤️褒めメッセージ機能は停止
                                for reaction in reactions:
                                    try:
                                        await file_message.add_reaction(reaction)
                                        await asyncio.sleep(0.5)  # Discord API レート制限対策
                                    except Exception as e:
                                        logger.warning(f"リアクション追加エラー ({reaction}): {e}")
                                
                                logger.info("メモファイルにリアクションを追加しました")
                                
                                # Discord投稿後、attachmentsフォルダの中身を削除
                                for attachment_file in attachments_dir.iterdir():
                                    if attachment_file.is_file():
                                        attachment_file.unlink()
                                        logger.info(f"添付ファイル削除: {attachment_file}")
                                
                            except Exception as upload_error:
                                logger.error(f"ファイル投稿エラー: {upload_error}")
                                # エラーが発生してもファイルは削除する
                                try:
                                    file_path.unlink()
                                    logger.info(f"エラー後のファイル削除: {file_path}")
                                except Exception as cleanup_error:
                                    logger.warning(f"ファイル削除エラー: {cleanup_error}")
                                raise upload_error
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー (メモ機能): {e}")
                            await channel.send(f"{user.mention} ❌ メモの生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send(f"{user.mention} ❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send(f"{user.mention} ⚠️ メッセージに内容がありません。")
            
            # 📝 メモ：記事作成
            elif payload.emoji.name == '📝':
                # メッセージ内容または添付ファイル、Embedからテキストを取得
                input_text = message.content
                
                # Embedがある場合は内容を抽出
                embed_content = extract_embed_content(message)
                if embed_content:
                    if input_text:
                        input_text += f"\n\n【Embed内容】\n{embed_content}"
                    else:
                        input_text = embed_content
                    logger.info("Embed内容を追加")
                
                # 添付ファイルがある場合、テキストファイルの内容を読み取り
                if message.attachments:
                    for attachment in message.attachments:
                        file_content = await read_text_attachment(attachment)
                        if file_content:
                            if input_text:
                                input_text += f"\n\n【ファイル: {attachment.filename}】\n{file_content}"
                            else:
                                input_text = f"【ファイル: {attachment.filename}】\n{file_content}"
                            logger.info(f"添付ファイルの内容を追加: {attachment.filename}")
                
                if input_text:
                    # URL検出・警告
                    await check_content_for_urls(input_text, user, channel)
                    
                    # 処理開始メッセージ
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} 📝 記事を作成するよ〜！ちょっと待っててね\n📎 元メッセージ: {message_link}")
                    
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # 記事用プロンプトを読み込み
                    article_prompt = None
                    
                    # 1. ユーザーのカスタムプロンプトをチェック
                    if user_data and user_data.get('custom_prompt_article'):
                        article_prompt = user_data['custom_prompt_article']
                        logger.info(f"ユーザー {user.name} のカスタムプロンプトを使用")
                    
                    # 2. カスタムプロンプトがない場合はデフォルトプロンプトファイルを使用
                    if not article_prompt:
                        prompt_path = script_dir / "prompt" / "article.txt"
                        if prompt_path.exists():
                            with open(prompt_path, 'r', encoding='utf-8') as f:
                                article_prompt = f.read()
                            logger.info("デフォルトプロンプトファイルを使用")
                        else:
                            article_prompt = "あなたは優秀なライターです。与えられた内容を元に、構造化された記事を作成してください。"
                            logger.info("フォールバックプロンプトを使用")
                    
                    # プロンプトにJSON出力指示を追加（既に含まれていない場合）
                    if '{"content":' not in article_prompt:
                        article_prompt += '\n\n出力はJSON形式で、以下のフォーマットに従ってください：\n{"content": "マークダウン形式の記事全文"}'
                    
                    # OpenAI APIで記事を生成（JSONモード）
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": article_prompt},
                                    {"role": "user", "content": input_text}
                                ],
                                max_tokens=3000,
                                temperature=0.7,
                                response_format={"type": "json_object"}
                            )
                            
                            # JSONレスポンスをパース
                            response_content = response.choices[0].message.content
                            try:
                                article_json = json.loads(response_content)
                                content = article_json.get("content", response_content)
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析エラー、フォールバックを使用: {response_content}")
                                content = response_content
                            
                            # ファイル名を生成（YYYYMMDD_HHMMSS_article.md）
                            now = datetime.now()
                            timestamp = now.strftime("%Y%m%d_%H%M%S")
                            filename = f"{timestamp}_article.md"
                            
                            # attachmentsフォルダにファイルを保存
                            attachments_dir = script_dir / "attachments"
                            attachments_dir.mkdir(exist_ok=True)
                            file_path = attachments_dir / filename
                            
                            # UTF-8でファイル保存
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            logger.info(f"記事ファイル作成: {file_path}")
                            
                            try:
                                # 記事のタイトルを抽出（最初の#行）
                                lines = content.split('\n')
                                title = "記事"
                                for line in lines:
                                    if line.strip().startswith('# '):
                                        title = line.strip()[2:].strip()
                                        break
                                
                                # 結果を送信
                                embed = discord.Embed(
                                    title="📝 記事を作成しました",
                                    description=f"**タイトル**: {title}\n**ファイル名**: `{filename}`",
                                    color=0x00bfa5
                                )
                                
                                # 内容のプレビュー（最初の300文字）
                                preview = content[:300] + "..." if len(content) > 300 else content
                                embed.add_field(
                                    name="📄 内容プレビュー",
                                    value=f"```markdown\n{preview}\n```",
                                    inline=False
                                )
                                
                                await channel.send(embed=embed)
                                
                                # ファイルをアップロード
                                with open(file_path, 'rb') as f:
                                    file_data = f.read()
                                
                                file_obj = io.BytesIO(file_data)
                                file_message = await channel.send("📝 記事ファイルです！", file=discord.File(file_obj, filename=filename))
                                
                                # 記事ファイルに自動でリアクションを追加
                                reactions = ['👍', '❓', '✏️', '📝']  # ❤️褒めメッセージ機能は停止
                                for reaction in reactions:
                                    try:
                                        await file_message.add_reaction(reaction)
                                        await asyncio.sleep(0.5)  # Discord API レート制限対策
                                    except Exception as e:
                                        logger.warning(f"リアクション追加エラー ({reaction}): {e}")
                                
                                logger.info("記事ファイルにリアクションを追加しました")
                                
                                # Discord投稿後、attachmentsフォルダの中身を削除
                                for attachment_file in attachments_dir.iterdir():
                                    if attachment_file.is_file():
                                        attachment_file.unlink()
                                        logger.info(f"添付ファイル削除: {attachment_file}")
                                
                            except Exception as upload_error:
                                logger.error(f"ファイル投稿エラー: {upload_error}")
                                # エラーが発生してもファイルは削除する
                                try:
                                    file_path.unlink()
                                    logger.info(f"エラー後のファイル削除: {file_path}")
                                except Exception as cleanup_error:
                                    logger.warning(f"ファイル削除エラー: {cleanup_error}")
                                raise upload_error
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー (記事機能): {e}")
                            await channel.send(f"{user.mention} ❌ 記事の生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send(f"{user.mention} ❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send(f"{user.mention} ⚠️ メッセージに内容がありません。")
            
            # 🌐 URL取得：URLからコンテンツを取得してテキストファイルとして保存
            elif payload.emoji.name == '🌐':
                # メッセージからURLを抽出
                urls = []
                if message.content:
                    urls = article_extractor.extract_urls_from_text(message.content)
                
                # EmbedからもURLを抽出
                if message.embeds:
                    for embed in message.embeds:
                        if embed.url:
                            urls.append(embed.url)
                        if embed.description:
                            embed_urls = article_extractor.extract_urls_from_text(embed.description)
                            urls.extend(embed_urls)
                
                if urls:
                    # 処理開始メッセージ
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} 🌐 URLの内容を取得するよ〜！ちょっと待っててね\n📎 元メッセージ: {message_link}")
                    
                    # 最初のURLのみ処理
                    url = urls[0]
                    
                    # ArticleExtractorを使用してコンテンツを取得
                    title, content, error = await article_extractor.fetch_article_content(url)
                    
                    if content and content.strip():
                        try:
                            # 英語コンテンツの判定と翻訳
                            is_english = is_english_content(content)
                            translated_content = None
                            translated_title = None
                            
                            if is_english:
                                logger.info("英語コンテンツを検出、翻訳を開始")
                                translated_content = await translate_text_to_japanese(content)
                                if title:
                                    translated_title = await translate_text_to_japanese(title)
                            
                            # ファイル名を生成（タイトルがある場合は使用）
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            display_title = translated_title if translated_title else title
                            safe_title = display_title[:30].replace("/", "_").replace("\\", "_").replace(":", "_") if display_title else "url_content"
                            filename = f"{timestamp}_{safe_title}.txt"
                            file_path = script_dir / "attachments" / filename
                            
                            # ファイルに保存
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(f"取得元URL: {url}\n")
                                f.write(f"記事タイトル: {title or 'タイトル取得失敗'}\n")
                                if translated_title:
                                    f.write(f"翻訳タイトル: {translated_title}\n")
                                f.write(f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                if is_english:
                                    f.write(f"言語: 英語 → 日本語翻訳済み\n")
                                f.write("=" * 50 + "\n\n")
                                
                                if translated_content:
                                    f.write("【日本語翻訳】\n")
                                    f.write(translated_content)
                                    f.write("\n\n" + "=" * 30 + "\n\n")
                                    f.write("【原文（英語）】\n")
                                
                                f.write(content)
                            
                            logger.info(f"URLコンテンツファイル作成: {file_path}")
                            
                            # プレビューは翻訳版を優先
                            preview_content = translated_content if translated_content else content
                            preview = preview_content[:150] + "..." if len(preview_content) > 150 else preview_content
                            
                            # 結果を送信
                            embed_title = "🌐 URLの内容を取得しました"
                            if is_english:
                                embed_title += " (日本語翻訳済み)"
                            
                            display_title_text = translated_title if translated_title else (title or 'タイトル取得失敗')
                            
                            embed = discord.Embed(
                                title=embed_title,
                                description=f"**URL**: {url}\n**タイトル**: {display_title_text}\n**ファイル名**: `{filename}`",
                                color=0x4285f4 if not is_english else 0x00ff00
                            )
                            
                            preview_name = "📄 記事内容プレビュー (最初の150文字)"
                            if is_english:
                                preview_name += " - 翻訳版"
                            
                            embed.add_field(
                                name=preview_name,
                                value=f"```\n{preview}\n```",
                                inline=False
                            )
                            
                            # 文字数情報を追加
                            info_text = f"記事文字数: {len(content):,}文字"
                            if is_english:
                                info_text += f"\n翻訳文字数: {len(translated_content):,}文字" if translated_content else ""
                                info_text += "\n🌍 言語: 英語 → 日本語"
                            
                            embed.add_field(
                                name="📊 情報",
                                value=info_text,
                                inline=True
                            )
                            
                            await channel.send(embed=embed)
                            
                            # ファイルをアップロード
                            with open(file_path, 'rb') as f:
                                file_data = f.read()
                            
                            file_obj = io.BytesIO(file_data)
                            upload_message = "🌐 URLの記事内容をテキストファイルにしました！\n✨ 記事本文のみを抽出しています"
                            if is_english:
                                upload_message = "🌐 URLの記事内容をテキストファイルにしました！\n🌍 英語記事を日本語に翻訳しました（原文も含まれています）"
                            
                            file_message = await channel.send(upload_message, file=discord.File(file_obj, filename=filename))
                            
                            # URLコンテンツファイルに自動でリアクションを追加
                            reactions = ['👍', '❓', '✏️', '📝', '👀', '🙌']  # ❤️褒めメッセージ機能は停止
                            for reaction in reactions:
                                try:
                                    await file_message.add_reaction(reaction)
                                    await asyncio.sleep(0.5)  # Discord API レート制限対策
                                except Exception as e:
                                    logger.warning(f"リアクション追加エラー ({reaction}): {e}")
                            
                            logger.info("URLコンテンツファイルにリアクションを追加しました")
                            
                            # ファイル削除
                            try:
                                file_path.unlink()
                                logger.info(f"一時ファイル削除: {file_path}")
                            except Exception as cleanup_error:
                                logger.warning(f"ファイル削除エラー: {cleanup_error}")
                            
                        except Exception as e:
                            logger.error(f"URLコンテンツ処理エラー: {e}")
                            await channel.send(f"{user.mention} ❌ ファイルの作成中にエラーが発生しました。")
                    else:
                        # エラーメッセージを詳細化
                        if error:
                            await channel.send(f"{user.mention} ❌ URLから記事を取得できませんでした。\n💡 **原因**: {error}")
                        else:
                            await channel.send(f"{user.mention} ❌ URLから記事を取得できませんでした。\n💡 記事が短すぎるか、アクセス制限が原因の可能性があります。")
                else:
                    await channel.send(f"{user.mention} ⚠️ メッセージにURLが見つかりません。")
            
            # 🙌 要約：URLから記事を取得して要約
            elif payload.emoji.name == '🙌':
                # メッセージからURLを抽出
                urls = []
                if message.content:
                    urls = article_extractor.extract_urls_from_text(message.content)
                
                # EmbedからもURLを抽出
                if message.embeds:
                    for embed in message.embeds:
                        if embed.url:
                            urls.append(embed.url)
                        if embed.description:
                            embed_urls = article_extractor.extract_urls_from_text(embed.description)
                            urls.extend(embed_urls)
                
                if urls:
                    # 処理開始メッセージ
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} 🙌 記事を要約するよ〜！ちょっと待っててね\n📎 元メッセージ: {message_link}")
                    
                    # 最初のURLのみ処理
                    target_url = urls[0]
                    
                    try:
                        # 記事コンテンツを取得
                        title, content, error = await article_extractor.fetch_article_content(target_url)
                        
                        if error:
                            await channel.send(f"{user.mention} ❌ 記事の取得に失敗しました: {error}")
                            return
                        
                        if not content:
                            await channel.send(f"{user.mention} ❌ 記事の本文を取得できませんでした。")
                            return
                        
                        # 要約プロンプトを読み込み
                        summary_prompt = None
                        
                        # 1. ユーザーのカスタムプロンプトをチェック
                        if user_data and user_data.get('custom_prompt_summary'):
                            summary_prompt = user_data['custom_prompt_summary']
                            logger.info(f"ユーザー {user.name} のカスタム要約プロンプトを使用")
                        
                        # 2. カスタムプロンプトがない場合はデフォルトプロンプトファイルを使用
                        if not summary_prompt:
                            prompt_path = script_dir / "prompt" / "summary.txt"
                            if prompt_path.exists():
                                with open(prompt_path, 'r', encoding='utf-8') as f:
                                    summary_prompt = f.read()
                                logger.info("デフォルト要約プロンプトファイルを使用")
                            else:
                                summary_prompt = "以下の記事を3行で要約し、キーフレーズを5個抽出してください。"
                                logger.info("フォールバック要約プロンプトを使用")
                        
                        # モデルを選択
                        model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                        
                        # OpenAI APIで要約を生成
                        if client_openai:
                            try:
                                # 記事データを構築
                                article_data = f"タイトル: {title}\n\n記事内容:\n{content}"
                                
                                response = client_openai.chat.completions.create(
                                    model=model,
                                    messages=[
                                        {"role": "system", "content": summary_prompt},
                                        {"role": "user", "content": article_data}
                                    ],
                                    max_tokens=1500,
                                    temperature=0.7
                                )
                                
                                summary_result = response.choices[0].message.content.strip()
                                
                                # タイトルが英語の場合は日本語に翻訳
                                display_title = title
                                if title and is_english_title(title):
                                    try:
                                        translate_response = client_openai.chat.completions.create(
                                            model="gpt-4.1-mini",  # 翻訳は軽量モデルで十分
                                            messages=[
                                                {"role": "system", "content": "以下の英語タイトルを自然な日本語に翻訳してください。技術記事のタイトルとして適切な日本語に翻訳し、元のニュアンスを保ってください。"},
                                                {"role": "user", "content": title}
                                            ],
                                            max_tokens=200,
                                            temperature=0.3
                                        )
                                        translated_title = translate_response.choices[0].message.content.strip()
                                        display_title = f"{translated_title}\n*原題: {title}*"
                                        logger.info(f"タイトル翻訳完了: {title} → {translated_title}")
                                    except Exception as e:
                                        logger.warning(f"タイトル翻訳エラー: {e}")
                                        display_title = title  # 翻訳失敗時は元のタイトルを使用
                                
                                # 結果をEmbedで送信
                                embed = discord.Embed(
                                    title="🙌 記事要約完了",
                                    color=0xffd700
                                )
                                
                                embed.add_field(
                                    name="📄 記事タイトル",
                                    value=display_title[:400] + "..." if display_title and len(display_title) > 400 else display_title or "（タイトル取得失敗）",
                                    inline=False
                                )
                                
                                embed.add_field(
                                    name="🔗 記事URL",
                                    value=target_url,
                                    inline=False
                                )
                                
                                embed.add_field(
                                    name="📝 要約結果",
                                    value=summary_result[:1000] + "..." if len(summary_result) > 1000 else summary_result,
                                    inline=False
                                )
                                
                                embed.set_footer(text=f"記事文字数: {len(content):,}文字 | モデル: {model}")
                                
                                await channel.send(embed=embed)
                                
                                logger.info(f"記事要約完了: {target_url}")
                                
                            except Exception as e:
                                logger.error(f"OpenAI API エラー (要約機能): {e}")
                                await channel.send(f"{user.mention} ❌ 要約の生成中にエラーが発生しました。")
                        
                        else:
                            logger.error("エラー: OpenAI APIキーが設定されていません")
                            await channel.send(f"{user.mention} ❌ エラーが発生しました。管理者にお問い合わせください。")
                        
                    except Exception as e:
                        logger.error(f"記事要約処理エラー: {e}")
                        await channel.send(f"{user.mention} ❌ 記事の要約中にエラーが発生しました。")
                
                else:
                    await channel.send(f"{user.mention} ⚠️ メッセージにURLが見つかりません。記事のURLを含むメッセージに🙌リアクションしてください。")
            
            # 👀 Xツリー投稿生成：メッセージ内容からエンゲージメント重視のツリー投稿を生成
            elif payload.emoji.name == '👀':
                # プレミアムユーザーチェック
                if not await is_premium_user(str(user.id)):
                    user_data = load_user_data(str(user.id))
                    if user_data["daily_usage"] >= FREE_USER_DAILY_LIMIT:
                        await channel.send(f"{user.mention} ⚠️ 1日の利用制限（{FREE_USER_DAILY_LIMIT}回）に達しました。")
                        return
                    else:
                        user_data["daily_usage"] += 1
                        save_user_data(str(user.id), user_data)
                
                # メッセージ内容を取得
                content_to_process = ""
                
                # メッセージ本文
                if message.content:
                    content_to_process += message.content + "\n\n"
                
                # 添付ファイルの内容を読み込み
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.filename.endswith(('.txt', '.md')):
                            try:
                                attachment_content = await read_text_attachment(attachment)
                                if attachment_content:
                                    content_to_process += f"【ファイル: {attachment.filename}】\n{attachment_content}\n\n"
                            except Exception as e:
                                logger.warning(f"添付ファイル読み込みエラー: {e}")
                
                # Embedの内容を抽出
                if message.embeds:
                    embed_content = extract_embed_content(message)
                    if embed_content:
                        content_to_process += f"【Embed情報】\n{embed_content}\n\n"
                
                if content_to_process.strip():
                    # 処理開始メッセージ
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    await channel.send(f"{user.mention} 👀 注目を集めるツリー投稿を作成します！少々お待ちください\n📎 元メッセージ: {message_link}")
                    
                    try:
                        # プロンプトファイルを読み込み
                        thread_prompt_path = script_dir / "prompt" / "thread.txt"
                        if thread_prompt_path.exists():
                            with open(thread_prompt_path, 'r', encoding='utf-8') as f:
                                thread_prompt = f.read()
                            
                            # {content}を実際の内容に置換
                            thread_prompt = thread_prompt.replace("[ここに解説したいニュース記事のURLや文章を入力してください]", content_to_process.strip())
                        else:
                            # フォールバック用のシンプルなプロンプト
                            thread_prompt = f"""
以下の内容を、読者が最後まで読みたくなるXツリー投稿（3-7ツイート）に変換してください。
各ツイートは140字以内で、エンゲージメントを重視した構成にしてください。

【ツイート 1/n】
【ツイート 2/n】
【ツイート 3/n】

対象コンテンツ:
{content_to_process.strip()}
"""
                        
                        if OPENAI_API_KEY:
                            # OpenAI APIを使用してツリー投稿生成
                            model = PREMIUM_USER_MODEL if await is_premium_user(str(user.id)) else FREE_USER_MODEL
                            
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": "あなたは読者の心を掴むXツリー投稿の専門家です。"},
                                    {"role": "user", "content": thread_prompt}
                                ],
                                max_tokens=1500,
                                temperature=0.7
                            )
                            
                            thread_result = response.choices[0].message.content.strip()
                            
                            # ツイートを解析して分割
                            import re
                            tweet_pattern = r'【ツイート\s*(\d+)/(\d+)】([^【]*?)(?=【ツイート|\Z)'
                            tweets = re.findall(tweet_pattern, thread_result, re.DOTALL)
                            
                            if not tweets:
                                # パターンマッチしない場合は改行で分割
                                lines = thread_result.split('\n')
                                tweets = []
                                current_tweet = ""
                                tweet_num = 1
                                
                                for line in lines:
                                    line = line.strip()
                                    if line and not line.startswith('【'):
                                        if len(current_tweet + line) <= 140:
                                            current_tweet += line + " "
                                        else:
                                            if current_tweet:
                                                tweets.append((str(tweet_num), str(len(tweets)+1), current_tweet.strip()))
                                                tweet_num += 1
                                            current_tweet = line + " "
                                
                                if current_tweet:
                                    tweets.append((str(tweet_num), str(len(tweets)+1), current_tweet.strip()))
                            
                            if tweets:
                                # 1ツイート目から画像生成
                                first_tweet_content = tweets[0][2] if tweets else ""
                                image_url = await generate_thread_image(first_tweet_content)
                                
                                # ヘッダーEmbedを作成
                                header_embed = discord.Embed(
                                    title=f"👀 Xツリー投稿（{len(tweets)}ツイート）",
                                    description="エンゲージメント重視のツリー投稿を生成しました",
                                    color=0xff6b6b
                                )
                                
                                # 画像を設定
                                image_file = None
                                if image_url:
                                    if image_url.startswith('http'):
                                        # URL形式の場合
                                        header_embed.set_image(url=image_url)
                                        header_embed.add_field(name="🎨", value="AI生成画像付き", inline=True)
                                    else:
                                        # ファイルパス形式の場合（base64から生成された一時ファイル）
                                        import pathlib
                                        temp_path = pathlib.Path(image_url)
                                        if temp_path.exists():
                                            image_file = discord.File(str(temp_path), filename="ai_generated_image.png")
                                            header_embed.set_image(url="attachment://ai_generated_image.png")
                                            header_embed.add_field(name="🎨", value="AI生成画像付き", inline=True)
                                
                                # 1ツイート目のX投稿リンク
                                if tweets:
                                    first_tweet = tweets[0][2].strip()
                                    import urllib.parse
                                    # 140文字制限内で適切に切り取り（日本語考慮）
                                    max_chars = 135  # URL短縮やハッシュタグのためのマージン
                                    if len(first_tweet) > max_chars:
                                        # 文末が不自然にならないよう調整
                                        short_tweet = first_tweet[:max_chars].rstrip('。、！？')
                                        # 文の途中で切れる場合は前の文で終了
                                        last_period = max(short_tweet.rfind('。'), short_tweet.rfind('！'), short_tweet.rfind('？'))
                                        if last_period > max_chars * 0.5:  # 半分以上の文字があれば採用
                                            short_tweet = short_tweet[:last_period + 1]
                                        # 空文字になった場合は元の短縮版を使用
                                        if not short_tweet.strip():
                                            short_tweet = first_tweet[:max_chars]
                                    else:
                                        short_tweet = first_tweet
                                    
                                    # 最終的に空文字の場合は代替テキストを使用
                                    if not short_tweet.strip():
                                        short_tweet = "興味深い内容をシェアします"
                                    
                                    # 日本語対応URLエンコード
                                    encoded_tweet = urllib.parse.quote(short_tweet, safe='')
                                    x_post_url = f"https://x.com/intent/post?text={encoded_tweet}"
                                    
                                    # デバッグ：URL生成をログ出力
                                    logger.info(f"X投稿URL生成: 元テキスト={first_tweet[:50]}...")
                                    logger.info(f"X投稿URL生成: 短縮テキスト={short_tweet[:50]}...")
                                    logger.info(f"X投稿URL生成: URL長={len(x_post_url)}")
                                    
                                    # URL全体が長すぎる場合はシンプルなリンクにする
                                    if len(x_post_url) > 900:  # 安全マージン
                                        header_embed.add_field(
                                            name="🔗 X投稿リンク",
                                            value="[X で投稿する](https://x.com/intent/post)",
                                            inline=False
                                        )
                                    else:
                                        header_embed.add_field(
                                            name="🔗 X投稿リンク",
                                            value=f"[1ツイート目をXで投稿]({x_post_url})",
                                            inline=False
                                        )
                                
                                header_embed.add_field(
                                    name="💡 使い方",
                                    value="各ツイートをコピーして順番にX(旧Twitter)に投稿してください",
                                    inline=False
                                )
                                
                                # ヘッダーEmbedを送信（画像ファイルがある場合は添付）
                                if image_file:
                                    await channel.send(embed=header_embed, file=image_file)
                                else:
                                    await channel.send(embed=header_embed)
                                
                                # 各ツイートを個別のEmbedとして送信
                                for i, (tweet_num, total, content) in enumerate(tweets):
                                    tweet_text = content.strip()
                                    # Discord Embedのdescription制限は4096文字だが、コードブロック考慮で安全に制限
                                    if len(tweet_text) > 4000:
                                        tweet_text = tweet_text[:4000] + "..."
                                    
                                    tweet_embed = discord.Embed(
                                        title=f"📱 ツイート {tweet_num}/{len(tweets)}",
                                        description=f"```\n{tweet_text}\n```",
                                        color=0x1da1f2  # Twitter blue
                                    )
                                    
                                    await channel.send(embed=tweet_embed)
                                logger.info(f"👀ツリー投稿生成完了: {len(tweets)}ツイート")
                                
                                # 一時画像ファイルのクリーンアップ
                                if image_url and not image_url.startswith('http'):
                                    try:
                                        import pathlib
                                        temp_path = pathlib.Path(image_url)
                                        if temp_path.exists():
                                            temp_path.unlink()  # ファイル削除
                                            logger.info(f"一時画像ファイルを削除: {temp_path}")
                                    except Exception as cleanup_error:
                                        logger.warning(f"一時ファイル削除エラー: {cleanup_error}")
                            
                            else:
                                await channel.send(f"{user.mention} ❌ ツリー投稿の生成に失敗しました。")
                        
                        else:
                            logger.error("エラー: OpenAI APIキーが設定されていません")
                            await channel.send(f"{user.mention} ❌ エラーが発生しました。管理者にお問い合わせください。")
                    
                    except Exception as e:
                        logger.error(f"👀ツリー投稿生成エラー: {e}")
                        await channel.send(f"{user.mention} ❌ ツリー投稿の生成中にエラーが発生しました。")
                
                else:
                    await channel.send(f"{user.mention} ⚠️ メッセージに内容がありません。テキストや添付ファイルがあるメッセージに👀リアクションしてください。")

@bot.event
async def on_message(message):
    """メッセージ受信時の処理"""
    # Botのメッセージは無視
    if message.author.bot:
        return
    
    # コマンドの処理を継続
    await bot.process_commands(message)



if __name__ == "__main__":
    if TOKEN is None:
        logger.error("エラー: DISCORD_BOT_TOKEN 環境変数が設定されていません")
    else:
        try:
            logger.info("Botを起動しています...")
            bot.run(TOKEN)
        except Exception as e:
            logger.error(f"Bot起動エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())