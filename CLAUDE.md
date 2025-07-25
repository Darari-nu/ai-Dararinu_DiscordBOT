# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with the AI Darari-nu Discord Bot codebase.

## 🌐 PRODUCTION DEPLOYMENT STATUS

**✅ LIVE ON XSERVER VPS ✅**

The AI Darari-nu Discord Bot is deployed and running 24/7 on Xserver VPS with full stability.

### Production Environment
- **Server**: Xserver VPS (Ubuntu 24.04 LTS)  
- **Location**: `/opt/ai-Dararinu_DiscordBOT/`
- **Service**: `ai-darari-nu-bot.service` (systemd)
- **Status**: Active and monitored with auto-restart
- **Co-located**: Discord RSS Bot (AI News Bot)
- **Python**: 3.12+ with virtual environment
- **Dependencies**: All packages in requirements.txt installed

### Deployment Information
- **IP**: 210.131.217.175 (Xserver VPS)
- **User**: root
- **Deploy Date**: 2025-07-22 (Initial), Updated: 2025-07-25
- **Auto-start**: Yes (systemd enabled)
- **Log Location**: `journalctl -u ai-darari-nu-bot`
- **Service File**: `/etc/systemd/system/ai-darari-nu-bot.service`

### Repository & Git Information
- **Repository**: https://github.com/Darari-nu/ai-Dararinu_DiscordBOT.git
- **Branch**: main (production)
- **Deploy Path**: `/opt/ai-Dararinu_DiscordBOT/`
- **Local Dev Path**: `/Users/watanabehidetaka/Claudecode/Action_Discord_BOT/ai-Darari-nu/`

**⚠️ IMPORTANT: Local vs Production**
- **Local directory**: Development and testing only
- **VPS directory**: Production environment 
- Changes pushed to GitHub main branch are available for VPS updates via `git pull`

### Public Information
- **Bot Invite**: Through Discord Developer Portal or Bot administrator
- **Repository**: Public on GitHub
- **Documentation**: README.md and CLAUDE.md
- **Update Method**: Push to GitHub repository

### Security Configuration
- **Sensitive Data**: All API keys and tokens in `.env` file (not tracked by git)
- **Environment Variables**: `DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`
- **File Permissions**: Restricted to root user on VPS
- **Port Configuration**: No external port exposure (Discord WebSocket only)
- **SSL/TLS**: Handled by Discord's infrastructure

## 🐛 Issue History & Fixes (2025-07-25)

### Recent Critical Issues Fixed:

#### **Issue #1: 👀機能 - OpenAI画像生成安全システム拒否エラー**
- **症状**: `safety system. Image descriptions generated from your prompt may contain text that is not allowed`
- **原因**: 1ツイート目の内容に「失敗」「問題」等のネガティブ表現が含まれ、OpenAIの安全フィルターに引っかかった
- **修正**: 
  - 画像生成プロンプトのネガティブ表現を安全な表現に置換（失敗→経験、問題→課題、危険→注意、リスク→考慮点）
  - エラーハンドリング強化：画像生成失敗時も処理続行
  - ログレベル改善：安全システム拒否の詳細ログ追加

#### **Issue #2: 👀機能 - Discord Embed文字数制限エラー** 
- **症状**: `Invalid Form Body In embeds.0.fields.0.value: Must be 1024 or fewer in length`
- **原因**: 新しいプロンプトで生成されるツイートが長文化し、Embed description制限(4096文字)を超過
- **修正**: 
  - ツイートテキスト制限を1000文字→4000文字に拡張（コードブロック考慮）
  - 長文ツイートの適切な切り捨て処理追加

#### **Issue #3: 👀機能 - プロンプト置換エラー**
- **症状**: `対象コンテンツが入力されていません`エラー表示
- **原因**: thread.txtプロンプト更新時に置換対象文字列が変更されたが、コードの置換処理が古い文字列を参照
- **修正**: 置換文字列を新プロンプトに合わせて更新：
  - 旧: `[ここに要約・作成したい文章やキーワード、テーマなどを入力してください]`
  - 新: `[ここに解説したいニュース記事のURLや文章を入力してください]`

#### **Issue #4: 👀機能 - Embed出力への反応エラー**
- **症状**: Embed出力に👀リアクションしても「メッセージに内容がありません」エラー
- **原因**: `extract_embed_content(message.embeds)`と間違った引数を渡していた
- **修正**: `extract_embed_content(message)`に修正

#### **Issue #5: スマホでのコピー問題**
- **症状**: 1つのEmbedの複数fieldがスマホで繋がって表示され、個別コピーできない
- **修正**: 
  - 各ツイートを個別のEmbedとして送信
  - コードブロック(```)でコピーボタン追加
  - ヘッダーEmbed + 個別ツイートEmbedの構成に変更

#### **Issue #6: 👀機能 - OpenAI画像生成安全フィルター強化**
- **症状**: 日本語の比喩表現（「頭を殴られた」等）が英訳時にOpenAI安全システムに拒否される
- **原因**: 翻訳後の英語表現「hit in the head」「shocked」等が暴力的と判定
- **修正**:
  - 包括的な安全フィルター辞書を追加（日本語・英語両対応）
  - 日本語: 殴られた→驚いた、頭を殴られた→驚きを感じた、衝撃→印象
  - 英語: hit in the head→surprised、shocked→impressed、attack→approach
  - プロンプトスタイルを「business infographic」に変更
  - 文字数を100文字に制限してリスク軽減

#### **Issue #7: 👀機能 - ヘッダーEmbed文字数制限エラー**
- **症状**: `Invalid Form Body In embeds.0.fields.1.value: Must be 1024 or fewer in length`
- **原因**: X投稿URLが長文ツイート時に1024文字制限を超過
- **修正**:
  - X投稿用ツイートを100文字に制限
  - URL全体が900文字超過時はシンプルリンクにフォールバック
  - Discord Embed field制限を確実に回避

#### **Issue #8: 👀機能 - 断続的エラーの原因分析**
- **症状**: エラーが出たり出なかったりする不安定な動作
- **分析結果**: URLの種類ではなく一時的なDiscord接続問題が原因
- **詳細**: 
  - `11:18:27`: Discord API接続切断時のみエラー（`Attempting a reconnect`）
  - OpenAI処理は全て成功、Discord送信時のみ失敗
  - GoogleニュースURL含む全てのコンテンツで正常動作確認済み
- **対策**: 既存の自動再接続機能で解決済み

#### **Issue #9: 👀機能 - Imagenモデル更新とシンタックスエラー修正**
- **症状**: `gpt-image-1`モデルでの組織認証エラーとコード内のシンタックスエラー
- **原因**: 
  - gpt-image-1モデルがorganization verification要求
  - generate_thread_image関数内のインデント不整合
  - 未使用importによるコード肥大化
- **修正**:
  - モデルを`gpt-image-1`→`gpt-image-2`に変更
  - 品質設定を`medium`→`low`に変更（コスト最適化）
  - try-except文の正しいインデント調整
  - 未使用import削除（urllib.parse, PIL, random, io等）
  - コード構造の最適化

#### **Issue #10: 👍機能 - urllib.parse モジュールエラー**
- **症状**: 👍機能でURL含むメッセージ処理時に`NameError: name 'urllib' is not defined`エラー
- **原因**: 👍機能でX投稿URL生成時に`urllib.parse.quote()`を使用しているが、importが不足
- **修正**:
  - main.py 1862行目に`import urllib.parse`を追加
  - URLエンコード処理を正常化
  - 👍機能のX投稿生成が完全復旧

#### **Issue #11: 🌐機能 - 自動リアクション不足**
- **症状**: 🌐機能後に👀と🙌リアクションが自動追加されない
- **原因**: 自動リアクション配列に👀と🙌が含まれていない
- **修正**:
  - reactions配列を`['👍', '❓', '✏️', '📝']`→`['👍', '❓', '✏️', '📝', '👀', '🙌']`に拡張
  - 🌐機能後に6つの関連機能リアクションが自動追加

### Current Status (Updated 2025-07-25):
- ✅ **全ての既知の問題は修正済み** 
- ✅ **👀機能は完全安定稼働中**（画像生成含む）
- ✅ **画像生成成功率大幅向上**（安全フィルター強化）
- ✅ **スマホ・デスクトップ両対応のUX実現**
- ✅ **GoogleニュースURL含む全コンテンツ対応**
- ✅ **Discord接続エラー時の自動復旧確認済み**
- ✅ **gpt-image-1モデルで安定画像生成**（組織認証済み）
- ✅ **コード構造とインデント問題完全解決**

## 🏗️ Architecture Overview

### Core Bot Features & Functionality
The AI Darari-nu Bot provides 8 main features through reaction-based interaction:

#### **Core Features:**
1. **👍 X投稿生成** - メッセージ・ファイルをX用に要約・最適化
2. **🎤 音声文字起こし** - 音声・動画ファイルをWhisper APIでテキスト化  
3. **❓ AI解説** - 内容について詳しく解説・質問回答
4. **✏️ メモ作成** - Obsidian用Markdownメモ自動生成
5. **📝 記事作成** - PREP法に基づく構造化記事生成
6. **🌐 URL取得** - URLからコンテンツ抽出・テキストファイル化
7. **🙌 記事要約** - URL記事の3行要約・キーフレーズ抽出
8. **👀 Xツリー投稿** - エンゲージメント重視のツリー投稿生成（AI画像付き）

### Technical Architecture
The bot uses a reaction-based architecture where users interact via emoji reactions on messages. Key components:

1. **Premium System**: Triple-layered authentication
   - Discord role check in community server
   - Owner user ID fallback (settings.json)
   - Server owner auto-detection

2. **Content Processing Pipeline**:
   - `extract_embed_content()`: Processes Discord embeds
   - `read_text_attachment()`: Async file reading with encoding detection
   - Each reaction handler processes: original message → attachments → embeds

3. **File Generation**: All file uploads now include descriptive messages for mobile compatibility
   - Transcription files: "📄 文字起こし結果のテキストファイルです！"
   - Praise images: "🎉 褒め画像をお作りしました！"
   - Memo files: "📝 メモファイルを作成しました！"

### OpenAI Integration
- **Text Generation**: 
  - Free users: `gpt-4.1-mini`
  - Premium users: `gpt-4.1`
- **Audio Transcription**: Whisper API (`whisper-1` model)
- **Image Generation**: `gpt-image-1` model (Imagen, organization verified)
  - Size: 1536x1024 (landscape)
  - Quality: medium
  - Style: Clay figure aesthetic with natural lighting
- **Custom Prompts**: Loaded from `prompt/` directory at runtime

### Data Management & Storage
- **Server Settings**: `data/server_data/{server_id}.json`
  - Active channels, custom prompts, server configuration
- **User Data**: `data/user_data/{user_id}.json`
  - Usage tracking, premium status, daily limits
- **Temporary Files**: `attachments/` directory
  - Auto-cleaned after processing
  - Supports: txt, md, json, csv, log, py, js, html, css, xml
  - Audio/Video: mp3, m4a, ogg, webm, wav, mp4
- **Logging**: Custom `SyncFriendlyFileHandler` with rotation

### File Processing Pipeline
1. **Content Extraction**: Messages → Embeds → Attachments
2. **Encoding Detection**: UTF-8 and Shift-JIS support  
3. **Content Validation**: Safety filters and format checks
4. **AI Processing**: Model selection based on user tier
5. **Response Generation**: Discord Embeds with copy functionality


## 🔧 Recent Major Updates (2025-07-22)

### **Fixed Issues:**
1. **Automatic Reaction Spam** - Removed unwanted auto-reactions on user messages
2. **Premium Detection Bug** - Fixed owner detection priority in community server checks  
3. **Heart Feature Archive** - Moved ❤️ praise feature to `archived_features/` with restoration docs

### **New Features:**
1. **Xserver VPS Deployment** - Full production deployment with systemd service
2. **Premium Role Management** - Local server premium role system (Premium role ID: 1397188911486210138)
3. **Improved Error Handling** - Better debugging and systematic troubleshooting

## 🎯 Premium Management System

**Current Configuration:**
- **Community Server**: Dara Museum (1073542600033849446) 
- **Premium Role**: Premium (1397188911486210138)
- **Owner User**: 982891457000136715 (unlimited access)
- **Free User Limit**: 5 uses/day

**Premium Authentication Priority:**
1. **Owner User ID** (highest priority) - from settings.json
2. **Discord Server Owner** - automatic detection  
3. **Premium Role** - in community server
4. **Fallback**: Free user (5/day limit)

## 🔥 👀 Xツリー投稿機能（新機能実装予定）

### **機能概要**
メッセージに👀リアクションで、エンゲージメント重視のXツリー投稿（3-7ツイート）を自動生成する機能

### **仕様詳細**
- **プロンプト**: `prompt/thread.txt` - 「X心理コピーライター」ペルソナ
- **出力**: Discord Embed形式で各ツイートを構造化表示
- **文字数**: 各ツイート140字以内厳守
- **構成**: フック→予告→詳細展開→対話促進

### **UI/UX設計**
1. **Discord Embed表示**:
   ```
   👀 Xツリー投稿（5ツイート）
   ┌──────────────────────┐
   │ 📱 ツイート1/5       │
   │ [内容] 📋コピー      │
   ├──────────────────────┤
   │ 📱 ツイート2/5       │ 
   │ [内容] 📋コピー      │
   └──────────────────────┘
   ```

2. **機能要素**:
   - **各ツイートにコピーボタン**: 📋 個別コピー可能
   - **1ツイート目のX投稿リンク**: `https://x.com/intent/post?text=[1ツイート目URLエンコード]`
   - **全体コピー機能**: 全ツイートをまとめてコピー

### **技術実装ポイント**
- `thread.txt`から`{content}`部分を実際のメッセージ内容に置換
- URLエンコード処理で日本語対応
- Discord Embedの各fieldにコピーボタン風UI
- X APIは使用せず、intent URLで投稿支援

## Critical Implementation Notes

1. **File Upload Messages**: Always include descriptive text with file uploads for mobile Discord compatibility

2. **Japanese Filename Handling**: Discord strips Japanese characters from filenames. Solution: use English filenames with Japanese content inside files

3. **Automatic Reactions**: Only add reactions to bot-generated files (transcriptions, memos, articles), NOT to user messages

4. **Encoding**: Handle both UTF-8 and Shift-JIS for text file reading

5. **Rate Limiting**: Free users limited to 5 uses/day, tracked in user data JSON

## 🚀 Deployment Guide

### **Prerequisites:**
- sshpass: `brew install hudochenkov/sshpass/sshpass` (macOS)
- SSH access to Xserver VPS
- GitHub repository access

### **Full Deployment Steps:**
```bash
# 1. SSH Connection Test
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "echo 'Connection test'"

# 2. Clone Repository
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "
cd /opt && 
git clone https://github.com/Darari-nu/ai-Dararinu_DiscordBOT.git &&
cd ai-Dararinu_DiscordBOT
"

# 3. Setup Python Environment
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "
cd /opt/ai-Dararinu_DiscordBOT &&
python3 -m venv venv &&
source venv/bin/activate &&
pip install --upgrade pip &&
pip install -r requirements.txt
"

# 4. Install FFmpeg
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "
apt-get update &&
apt-get install -y ffmpeg
"

# 5. Create Environment File
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "
cd /opt/ai-Dararinu_DiscordBOT &&
cat > .env << 'EOF'
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
EOF
"

# 6. Create systemd Service
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "
cat > /etc/systemd/system/ai-darari-nu-bot.service << 'EOF'
[Unit]
Description=AI Darari-nu Discord Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-Dararinu_DiscordBOT
Environment=PATH=/opt/ai-Dararinu_DiscordBOT/venv/bin
ExecStart=/opt/ai-Dararinu_DiscordBOT/venv/bin/python /opt/ai-Dararinu_DiscordBOT/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
"

# 7. Enable and Start Service
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175 "
systemctl daemon-reload &&
systemctl enable ai-darari-nu-bot &&
systemctl start ai-darari-nu-bot &&
systemctl status ai-darari-nu-bot
"
```

## 🔧 Comprehensive Troubleshooting Guide

### **Critical Operational Issues:**

#### **1. Bot Service Management**
**Check Bot Status:**
```bash
ssh root@210.131.217.175 'systemctl status ai-darari-nu-bot'
```

**View Real-time Logs:**
```bash
ssh root@210.131.217.175 'journalctl -u ai-darari-nu-bot -f'
```

**Common Service Commands:**
```bash
# Restart bot
ssh root@210.131.217.175 'systemctl restart ai-darari-nu-bot'

# Stop bot
ssh root@210.131.217.175 'systemctl stop ai-darari-nu-bot'

# Check service file
ssh root@210.131.217.175 'cat /etc/systemd/system/ai-darari-nu-bot.service'

# Update from GitHub and restart
ssh root@210.131.217.175 'cd /opt/ai-Dararinu_DiscordBOT && git pull && systemctl restart ai-darari-nu-bot'
```

#### **2. Image Generation Issues**

**Problem: 画像が表示されない**
**Diagnosis Steps:**
1. Check logs for `画像生成エラー` messages
2. Verify model availability in API response
3. Check organization verification status

**Common Errors & Solutions:**
```bash
# Error: Invalid model 'gpt-image-X'
# Solution: Use supported models only
- gpt-image-1 (requires organization verification)  
- gpt-image-0721-mini-alpha
- dall-e-2
- dall-e-3

# Error: Organization verification required
# Solution: Ensure API key has proper organization access
```

**Current Working Configuration:**
- Model: `gpt-image-1` (organization verified)
- Size: `1536x1024` (landscape)
- Quality: `medium`
- Style: Clay figure with natural lighting

#### **3. Discord Connection Issues**
**Symptoms:** Bot not responding to reactions
**Check List:**
1. **Channel Activation**: Run `/activate` in target channel
2. **Bot Permissions**: Ensure read messages, add reactions, send messages
3. **Discord Intents**: Verify privileged intents enabled in Developer Portal
4. **Network**: Check VPS connectivity to Discord API

#### **4. Premium System Issues**
**Priority Order (Highest to Lowest):**
1. settings.json owner_user_id: `982891457000136715`
2. Discord server owner detection (automatic)
3. Premium role check in community server
4. Fallback: Free user (5/day limit)

**Current Configuration:**
- Community Server: Dara Museum (`1073542600033849446`)
- Premium Role: Premium (`1397188911486210138`)
- Owner User: `982891457000136715`

### **Development & Deployment Issues:**

#### **5. SSH Connection Problems**
**Requirements:**
```bash
# Install sshpass (macOS)
brew install hudochenkov/sshpass/sshpass

# Connection command
sshpass -p "j-33008744444-" ssh -o StrictHostKeyChecking=no root@210.131.217.175
```

#### **6. File Processing Issues**
**Common Problems:**
- **Encoding Issues**: Code supports UTF-8 and Shift-JIS
- **File Size Limits**: Discord 25MB limit enforced
- **Format Support**: Check supported extensions in file processing pipeline

#### **7. OpenAI API Issues**
**Rate Limiting:**
- Monitor API usage in OpenAI dashboard
- Free users: gpt-4.1-mini for cost efficiency
- Premium users: gpt-4.1 for quality

**Safety System Errors:**
- Comprehensive safety filters implemented for image generation
- Japanese expressions translated safely to English
- Automatic fallback prompts for rejected content

### **Environment & Dependencies:**

#### **8. System Requirements**
**VPS Environment:**
- Ubuntu 24.04 LTS
- Python 3.12+ with venv
- FFmpeg for audio processing
- Git for code updates

**Required Packages:**
```bash
apt-get install -y ffmpeg python3-venv git
```

#### **9. Log Analysis**
**Important Log Patterns:**
```bash
# Success patterns
INFO:__main__:👀ツリー投稿生成完了
INFO:__main__:画像生成成功

# Error patterns  
ERROR:__main__:画像生成エラー
WARNING:__main__:OpenAI安全システムによる画像生成拒否

# Connection issues
INFO:disconnect.gateway:Attempting a reconnect
```

### **Quick Diagnostic Commands:**
```bash
# Full system check
ssh root@210.131.217.175 '
cd /opt/ai-Dararinu_DiscordBOT && 
echo "=== Git Status ===" && git status && 
echo "=== Service Status ===" && systemctl status ai-darari-nu-bot && 
echo "=== Recent Logs ===" && journalctl -u ai-darari-nu-bot --since "10 minutes ago"
'
```

## Session Logging

**IMPORTANT: Always maintain a session log in Log.md**

- Create and maintain a `Log.md` file to record all terminal interactions and session activities
- Log should include:
  - Task descriptions and outcomes
  - Commands executed and their results
  - File changes made
  - Error messages and resolutions
  - Progress updates and completion status
- Update the log file throughout the session to track progress
- This helps maintain visibility into development activities and debugging