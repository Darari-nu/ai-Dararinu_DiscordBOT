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
- **Deploy Date**: 2025-07-22
- **Auto-start**: Yes (systemd enabled)
- **Log Location**: `journalctl -u ai-darari-nu-bot`

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
The bot uses a reaction-based architecture where users interact via emoji reactions (👍🎤❓❤️✏️) on messages. Key components:

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

## Critical Implementation Notes

1. **File Upload Messages**: Always include descriptive text with file uploads for mobile Discord compatibility

2. **Japanese Filename Handling**: Discord strips Japanese characters from filenames. Solution: use English filenames with Japanese content inside files

3. **Automatic Reactions**: Only add reactions to bot-generated files (transcriptions, memos, articles), NOT to user messages

4. **Encoding**: Handle both UTF-8 and Shift-JIS for text file reading

5. **Rate Limiting**: Free users limited to 5 uses/day, tracked in user data JSON

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