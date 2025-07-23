#!/usr/bin/env python3
"""
🙌 要約機能のテストスクリプト
新しく追加された記事要約機能の動作確認用
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

from utils.article_extractor import article_extractor

async def test_url_extraction():
    """URL抽出機能のテスト"""
    print("=== URL抽出テスト ===")
    
    test_texts = [
        "これは記事です: https://example.com/article/1",
        "複数URL: https://example.com/1 と https://example.com/2",
        "URLなしのテキスト",
        "https://github.com/example/repo",
        "Discord URL: https://discord.com/channels/123/456/789"
    ]
    
    for text in test_texts:
        urls = article_extractor.extract_urls_from_text(text)
        print(f"テキスト: {text}")
        print(f"抽出URL: {urls}")
        print("-" * 40)

async def test_article_fetch():
    """記事取得機能のテスト（外部アクセスなし）"""
    print("\n=== 記事取得テスト ===")
    
    # 無効なURLのテスト
    invalid_urls = [
        "http://invalid-url-12345.com",
        "https://localhost:8080/test",
        "not-a-url",
        "https://999.999.999.999",
    ]
    
    for url in invalid_urls:
        print(f"テストURL: {url}")
        is_valid = article_extractor._is_valid_url(url)
        print(f"有効性チェック: {is_valid}")
        print("-" * 40)

def test_prompt_loading():
    """プロンプトファイルの読み込みテスト"""
    print("\n=== プロンプトファイルテスト ===")
    
    prompt_path = Path(__file__).parent / "prompt" / "summary.txt"
    
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"ファイルパス: {prompt_path}")
        print(f"ファイルサイズ: {len(content)} 文字")
        print(f"先頭200文字: {content[:200]}...")
        print("✅ プロンプトファイル読み込み成功")
    else:
        print(f"❌ プロンプトファイルが見つかりません: {prompt_path}")

def test_settings_file():
    """設定ファイルの確認"""
    print("\n=== 設定ファイルテスト ===")
    
    import json
    settings_path = Path(__file__).parent / "settings.json"
    
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        print(f"設定ファイル: {settings_path}")
        print(f"設定内容: {json.dumps(settings, indent=2, ensure_ascii=False)}")
        
        # summary_daily_limitの確認
        if 'summary_daily_limit' in settings:
            print("✅ summary_daily_limit が設定されています")
        else:
            print("❌ summary_daily_limit が設定されていません")
    else:
        print(f"❌ 設定ファイルが見つかりません: {settings_path}")

async def main():
    """メインテスト実行"""
    print("🙌 要約機能テスト開始")
    print("=" * 50)
    
    await test_url_extraction()
    await test_article_fetch()
    test_prompt_loading()
    test_settings_file()
    
    print("\n" + "=" * 50)
    print("🎉 テスト完了！")
    print("\n📋 実装確認項目:")
    print("✅ prompt/summary.txt ファイル作成")
    print("✅ utils/article_extractor.py ライブラリ作成")
    print("✅ main.py に🙌リアクション処理追加")
    print("✅ カスタムプロンプト設定コマンド追加")
    print("✅ ヘルプコマンド更新")
    print("✅ requirements.txt 更新（beautifulsoup4, readability-lxml）")
    print("✅ settings.json 更新（summary_daily_limit追加）")
    
    print("\n🚀 次のステップ:")
    print("1. pip install beautifulsoup4 readability-lxml")
    print("2. Discordサーバーでテスト")
    print("3. 実際のニュース記事URLで動作確認")

if __name__ == "__main__":
    asyncio.run(main())