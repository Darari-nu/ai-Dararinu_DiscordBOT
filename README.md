# 🤖 AI Darari-nu Bot

**リアクション一つで、あらゆるコンテンツをAIが最適化**

Discord上で8つのAI機能を提供する多機能Botです。メッセージにリアクション（絵文字）を付けるだけの直感的な操作で、X投稿生成、音声文字起こし、AI解説、メモ作成など、コンテンツ制作に必要な機能を一括提供します。

## ✨ 全機能一覧

### 🎯 **コア機能（8つ）**
1. **👍 X投稿生成** - メッセージ・ファイルをX（旧Twitter）投稿用に最適化
2. **🎤 音声文字起こし** - 音声・動画ファイルをWhisper APIでテキスト変換（MP4対応）
3. **❓ AI解説** - あらゆる内容について詳しく解説・質問回答
4. **✏️ メモ作成** - Obsidian用Markdownメモを自動生成
5. **📝 記事作成** - PREP法による構造化されたMarkdown記事生成
6. **🌐 URL取得** - ウェブ記事からテキスト抽出・日本語翻訳対応
7. **🙌 記事要約** - URL記事を3行要約＋キーフレーズ抽出（12k文字対応）
8. **👀 Xツリー投稿** - エンゲージメント重視のツリー投稿生成（**AI画像付き**）⭐NEW

### 🎨 **特別機能**
- **AI画像生成**: 👀機能で粘土フィギュア風の独創的な画像を自動生成
- **スマホ最適化UI**: 各ツイートに個別コピーボタン付きEmbed表示
- **多言語対応**: 英語記事の自動日本語翻訳
- **ファイル形式対応**: 10種類以上のテキスト・音声・動画ファイル

## 🎯 プラン比較

| 機能 | 無料プラン | プレミアムプラン |
|------|------------|------------------|
| **使用回数** | 1日5回まで | **無制限** |
| **AIモデル** | GPT-4o-mini | **GPT-4o（最高品質）** |
| **画像生成** | ✅ | ✅ |
| **音声文字起こし** | ✅ | ✅ |
| **カスタムプロンプト** | ✅ | ✅ |
| **全機能アクセス** | ✅ | ✅ |

## 🚀 Bot導入ガイド

### **Step 1: Bot招待**
1. **公式サイトにアクセス**
   - 🌐 **https://ai-darari-nu.kei31.com/**
   
2. **Botをサーバーに招待**
   - 必要な権限：メッセージ送信、リアクション追加、ファイル添付

### **Step 2: 初期設定**
```
/activate
```
↑ 使用したいチャンネルで実行（管理者権限必要）

### **Step 3: 使用開始**
**メッセージにリアクション（👍🎤❓✏️📝🌐🙌👀）を付けるだけ！**

### **プレミアムプラン**
- **対象サーバー**: Dara Museum Discord
- **ロール**: Premium
- **申込**: 公式サイトからお問い合わせ

## 🔄 使用例ワークフロー

### 🎵 **音声コンテンツ → SNS投稿**
1. **音声ファイルをアップロード** → 🎤 → **文字起こしテキスト**
2. **文字起こしファイル** → 👍 → **X投稿最適化**
3. **生成されたEmbed** → 👀 → **エンゲージメント重視のツリー投稿（AI画像付き）**

### 📰 **ニュース記事 → 分析記事**
1. **ニュースURL貼り付け** → 🌐 → **記事内容抽出**
2. **抽出テキストファイル** → ❓ → **AI解説・分析**
3. **解説内容** → 📝 → **PREP法による構造化記事**

### 💭 **アイデア → 完成記事**
1. **思考メモを投稿** → ✏️ → **Obsidianメモ**
2. **メモファイル** → 📝 → **構造化記事作成**
3. **記事内容** → 👀 → **SNS用ツリー投稿（画像付き）**

### 🌍 **海外記事 → 日本語コンテンツ**
1. **英語記事URL** → 🌐 → **自動翻訳＋テキスト抽出**
2. **翻訳ファイル** → 🙌 → **3行要約＋キーフレーズ**
3. **要約内容** → 👀 → **日本語ツリー投稿**

## 📁 対応ファイル形式

### **テキストファイル**
`.txt`, `.md`, `.json`, `.csv`, `.log`, `.py`, `.js`, `.html`, `.css`, `.xml`

### **音声・動画ファイル**  
`mp3`, `m4a`, `ogg`, `webm`, `wav`, `mp4`

### **特殊処理**
- **エンコーディング**: UTF-8, Shift-JIS自動判定
- **ファイルサイズ**: Discord上限25MBまで
- **音声品質**: Whisper APIによる高精度変換
- **処理方法**: ファイル添付されたメッセージにリアクションするだけ
- **Embed処理**: Bot生成のEmbedメッセージにもリアクション可能（再処理・連携利用）

## 🎨 👀機能詳細（AI画像生成付きツリー投稿）

### **機能概要**
メッセージに👀リアクションで、エンゲージメントを重視したXツリー投稿（3-7ツイート）を自動生成。各投稿に粘土フィギュア風のAI画像が付きます。

### **生成される内容**
- **ツリー構成**: 心理学的コピーライティング手法で構成
- **フック**: 読者の感情を揺さぶる導入
- **展開**: PREP法による論理的な説明
- **まとめ**: 行動促進する締めくくり
- **AI画像**: 内容に合わせた粘土フィギュア風画像（1536x1024）

### **UI特徴**
- **スマホ対応**: 各ツイートが個別Embedで表示
- **コピー機能**: 各ツイートにコピーボタン付き
- **X投稿連携**: 1ツイート目のX投稿リンク自動生成

## 🔧 技術仕様

### **AIモデル**
- **テキスト生成**: GPT-4o (Premium) / GPT-4o-mini (Free)
- **音声認識**: Whisper API (`whisper-1`)
- **画像生成**: Imagen (`gpt-image-1`) - 粘土フィギュア風スタイル

### **インフラ**
- **サーバー**: Xserver VPS (Ubuntu 24.04)
- **Python**: 3.12+ with venv
- **データベース**: JSON file-based storage
- **ログ**: systemd journal + custom rotation

### **セキュリティ**
- **API管理**: 環境変数（.env）でトークン管理
- **レート制限**: 無料ユーザー 5回/日制限
- **権限管理**: Discord role-based authentication
- **ファイル処理**: 一時ファイル自動削除

## 🛠️ 開発者向けセットアップ

### **リポジトリ情報**
- **GitHub**: https://github.com/Darari-nu/ai-Dararinu_DiscordBOT.git  
- **ブランチ**: main (production)
- **言語**: Python 3.12+
- **主要ライブラリ**: discord.py, openai, aiohttp, pydub

### **ローカル開発環境セットアップ**

#### **前提条件**
- Python 3.12+
- FFmpeg（音声処理用）
- Git

#### **インストール手順**
```bash
# 1. リポジトリクローン
git clone https://github.com/Darari-nu/ai-Dararinu_DiscordBOT.git
cd ai-Dararinu_DiscordBOT

# 2. 仮想環境作成・有効化
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 依存関係インストール
pip install -r requirements.txt

# 4. FFmpegインストール（音声処理用）
# Mac: brew install ffmpeg
# Ubuntu: apt-get install ffmpeg
# Windows: https://ffmpeg.org/download.html

# 5. 環境設定
cp .env.example .env
# .envファイルにAPI keyを設定
```

#### **環境変数設定（.env）**
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

#### **実行**
```bash
python main.py
```

### **プロダクション デプロイ**

#### **VPSサーバー情報**
- **Provider**: Xserver VPS
- **OS**: Ubuntu 24.04 LTS
- **Path**: `/opt/ai-Dararinu_DiscordBOT/`
- **Service**: systemd

#### **デプロイ手順**
```bash
# SSH接続
ssh root@210.131.217.175

# GitHub更新取得
cd /opt/ai-Dararinu_DiscordBOT
git pull

# サービス再起動
systemctl restart ai-darari-nu-bot

# ステータス確認
systemctl status ai-darari-nu-bot
```

#### **ログ確認**
```bash
# リアルタイムログ
journalctl -u ai-darari-nu-bot -f

# 過去のログ
journalctl -u ai-darari-nu-bot --since "1 hour ago"
```

## 📊 運用実績

### **安定性**
- **稼働率**: 99.9%（24/7運用）
- **レスポンス時間**: 平均2-5秒
- **処理能力**: 1000+リクエスト/日対応実績

### **機能成熟度**
- **👀ツリー投稿**: ✅ 完全安定稼働（AI画像生成含む）
- **音声文字起こし**: ✅ MP4対応・高精度変換
- **多言語翻訳**: ✅ 英日自動翻訳対応
- **スマホUI**: ✅ 個別コピーボタン対応

## 🆘 サポート・問い合わせ

### **公式サイト**
🌐 **https://ai-darari-nu.kei31.com/**

### **機能に関する質問**
- Bot使用方法
- プレミアムプラン申込
- カスタマイズ相談

### **技術的な問題**
- GitHub Issues: https://github.com/Darari-nu/ai-Dararinu_DiscordBOT/issues
- 開発者向けドキュメント: `CLAUDE.md`

### **開発協力**
- **貢献歓迎**: Pull Request, Issue報告
- **技術スタック**: Python, Discord.py, OpenAI API
- **開発ガイド**: `CLAUDE.md`のDevelopment Guide参照

## 📄 ライセンス・利用規約

### **利用許可**
- **個人利用**: ✅ 自由に利用可能
- **商用利用**: ⚠️ 事前相談必要
- **再配布**: ⚠️ ライセンス表記必要

### **免責事項**
- AI生成コンテンツの内容については利用者責任
- サービス停止・データ損失について開発者は責任を負いません
- OpenAI APIの利用規約に準拠

---

**🤖 AI Darari-nu Bot - リアクション一つで、あらゆるコンテンツをAIが最適化**

*最新バージョン: 2025-07-25 | 8機能完全対応 | 24/7安定稼働中*
