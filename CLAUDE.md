# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌐 PRODUCTION DEPLOYMENT STATUS

**✅ LIVE ON XSERVER VPS ✅**

This bot is now deployed and running 24/7 on Xserver VPS:

**Production Environment:**
- **Server**: Xserver VPS (Ubuntu 24.04)  
- **Location**: `/opt/ai-Dararinu_DiscordBOT/`
- **Service**: `ai-darari-nu-bot.service` (systemd)
- **Status**: Active and monitored
- **Co-located**: Discord RSS Bot (AI News Bot)

**Deployment Information:**
- **IP**: 210.131.217.175
- **User**: root
- **Deploy Date**: 2025-07-22
- **Auto-start**: Yes (systemd enabled)
- **Log Location**: `journalctl -u ai-darari-nu-bot`
- **Repository**: https://github.com/Darari-nu/ai-Dararinu_DiscordBOT.git
- **Deploy Path**: `/opt/ai-Dararinu_DiscordBOT/`
- **Service File**: `/etc/systemd/system/ai-darari-nu-bot.service`

**⚠️ IMPORTANT: Local vs Production**
- **Local directory**: Development and testing only
- **VPS directory**: Production environment 
- Changes pushed to GitHub main branch are automatically available for VPS updates

### Website Updates
- Website source: `/Users/dararinu/Dropbox/xPersonal/project/mp0059_program/20250613_ai_darari_nu/webpage/`
- Main file: `index.html` (all styles embedded)
- Deploy changes by pushing to GitHub (ai-Dararinu_DiscordBOT repository)

## Architecture Overview

### Core Bot Structure
The bot uses a reaction-based architecture where users interact via emoji reactions (👍🎤❓❤️✏️👀🌐🙌) on messages. Key components:

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
- Free users: `gpt-4.1-mini`
- Premium users: `gpt-4.1`
- Whisper API for audio transcription
- Custom prompts loaded from `prompt/` directory

### Data Management
- Server settings: `data/server_data/{server_id}.json`
- User data: `data/user_data/{user_id}.json` (includes usage tracking)
- Temporary files: `attachments/` (auto-cleaned after use)


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

## 🔧 Troubleshooting Guide

### **Common Issues:**

#### **1. "Community server not found" Warning**
```
WARNING:__main__:Community server not found: 1383696841450721442
```
**Solution:** Fixed by updating settings.json with correct Dara Museum server ID
```json
{
  "community_server_id": "1073542600033849446",
  "premium_role_id": "1397188911486210138"
}
```

#### **2. Auto-Reaction Spam (6 reactions on every message)**
**Problem:** Bot adding 👍❓✏️📝🎤🌐 to all user messages
**Solution:** Removed automatic reaction code from `on_message` function
**Keep:** Auto-reactions only on bot-generated files (transcriptions, memos, articles)

#### **3. Premium Detection Not Working**
**Problem:** Owner user still getting 5/day limit
**Solution:** Fixed premium detection priority order:
1. settings.json owner_user_id (highest priority)
2. Discord server owner detection
3. Premium role check
4. Fallback to free user

#### **4. SSH Connection Issues**
**Problem:** Permission denied or connection timeout
**Requirements:**
- Install sshpass: `brew install hudochenkov/sshpass/sshpass`
- Use exact credentials: `root@210.131.217.175` with password `j-33008744444-`
- Add connection flags: `-o StrictHostKeyChecking=no`

#### **5. FFmpeg Not Found Warning**
```
RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```
**Solution:** Install FFmpeg on VPS: `apt-get install -y ffmpeg`

#### **6. Bot Not Responding in Discord**
**Check List:**
1. Channel activation: Run `/activate` command first
2. Service status: `systemctl status ai-darari-nu-bot`
3. Check logs: `journalctl -u ai-darari-nu-bot -f`
4. Verify .env file exists with correct tokens
5. Ensure Discord privileged intents are enabled in Developer Portal

### **Management Commands:**
```bash
# Check bot status
ssh root@210.131.217.175 'systemctl status ai-darari-nu-bot'

# View real-time logs  
ssh root@210.131.217.175 'journalctl -u ai-darari-nu-bot -f'

# Restart bot
ssh root@210.131.217.175 'systemctl restart ai-darari-nu-bot'

# Stop bot
ssh root@210.131.217.175 'systemctl stop ai-darari-nu-bot'

# Update from GitHub
ssh root@210.131.217.175 'cd /opt/ai-Dararinu_DiscordBOT && git pull && systemctl restart ai-darari-nu-bot'
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