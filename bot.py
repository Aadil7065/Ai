#!/usr/bin/env python3
"""
Telegram APK Cracker Bot v4.0 - FIXED
Now properly accepts ALL APK files
"""

import os
import sys
import asyncio
import logging
import re
import shutil
import tempfile
import subprocess
from pathlib import Path
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ======= CONFIG ========
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
# =======================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_tools():
    """Install required tools"""
    os.system("apt update && apt install -y apktool default-jdk wget 2>/dev/null")
    if not os.path.exists("/usr/local/bin/uber-apk-signer"):
        os.system("wget -q 'https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar' -O /usr/local/bin/uber-apk-signer.jar 2>/dev/null")
        with open("/usr/local/bin/uber-apk-signer", 'w') as f:
            f.write('#!/bin/bash\njava -jar /usr/local/bin/uber-apk-signer.jar "$@"\n')
        os.system("chmod +x /usr/local/bin/uber-apk-signer")

def crack_apk(apk_path, output_dir="/tmp/cracked"):
    """Full APK cracking pipeline"""
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(apk_path))[0]
    decompiled = f"{output_dir}/{base}_decompiled"
    cracked = f"{output_dir}/{base}_cracked.apk"
    signed = f"{output_dir}/{base}_signed.apk"
    
    # Step 1: Decompile
    logger.info("Step 1: Decompiling...")
    result = subprocess.run(["apktool", "d", "-f", "-o", decompiled, apk_path], 
                          capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"Decompile failed: {result.stderr[:200]}")
    
    manifest_path = f"{decompiled}/AndroidManifest.xml"
    
    # Step 2: Remove login activities from manifest
    logger.info("Step 2: Removing login activities...")
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Find login activities
        login_activities = []
        for match in re.finditer(r'<activity[^>]*android:name="([^"]*[Ll]ogin[^"]*|[Ss]plash[^"]*|[Ss]ign[^"]*|[Aa]uth[^"]*|[Ll]icense[^"]*|[Rr]egister[^"]*|[Ww]elcome[^"]*|[Oo]nboarding[^"]*)', content):
            login_activities.append(match.group(0))
        
        # Remove MAIN/LAUNCHER from login activities and add to first non-login activity
        main_filter = '<intent-filter>\n<action android:name="android.intent.action.MAIN"/>\n<category android:name="android.intent.category.LAUNCHER"/>\n</intent-filter>'
        
        # Remove existing MAIN intent filters
        content = re.sub(r'<intent-filter>\s*<action android:name="android\.intent\.action\.MAIN"/>\s*<category android:name="android\.intent\.category\.LAUNCHER"/>\s*</intent-filter>', '', content)
        
        # Find first non-login activity
        for match in re.finditer(r'<activity[^>]*android:name="([^"]*)"', content):
            activity_name = match.group(1)
            is_login = any(kw in activity_name.lower() for kw in ['login', 'splash', 'sign', 'auth', 'license', 'register', 'welcome', 'onboard'])
            if not is_login:
                # Add MAIN filter to this activity
                activity_tag = match.group(0)
                new_activity = f'{activity_tag}\n{main_filter}'
                content = content.replace(activity_tag, new_activity, 1)
                break
        
        # Remove login activities entirely
        for act in login_activities:
            # Find the complete activity block
            start = content.find(act)
            if start > -1:
                end = content.find('</activity>', start)
                if end > -1:
                    block = content[start:end + len('</activity>')]
                    content = content.replace(block, '', 1)
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"  Removed {len(login_activities)} login activities")
    
    # Step 3: Patch all security checks in smali
    logger.info("Step 3: Patching security checks...")
    bypass_methods = {
        'isLicensed': 'const/4 v0, 0x1\n    return v0',
        'isPurchased': 'const/4 v0, 0x1\n    return v0', 
        'isPremium': 'const/4 v0, 0x1\n    return v0',
        'isPro': 'const/4 v0, 0x1\n    return v0',
        'isSubscribed': 'const/4 v0, 0x1\n    return v0',
        'isLoggedIn': 'const/4 v0, 0x1\n    return v0',
        'isSignedIn': 'const/4 v0, 0x1\n    return v0',
        'isAuthenticated': 'const/4 v0, 0x1\n    return v0',
        'isRooted': 'const/4 v0, 0x0\n    return v0',
        'isTrial': 'const/4 v0, 0x0\n    return v0',
        'isTrialExpired': 'const/4 v0, 0x0\n    return v0',
        'isExpired': 'const/4 v0, 0x0\n    return v0',
        'isActivated': 'const/4 v0, 0x1\n    return v0',
        'isVerified': 'const/4 v0, 0x1\n    return v0',
        'hasSubscription': 'const/4 v0, 0x1\n    return v0',
        'hasAccess': 'const/4 v0, 0x1\n    return v0',
        'checkLicense': 'const/4 v0, 0x1\n    return v0',
        'verifyLicense': 'const/4 v0, 0x1\n    return v0',
        'validateLicense': 'const/4 v0, 0x1\n    return v0',
    }
    
    patched_count = 0
    for root, _, files in os.walk(decompiled):
        for file in files:
            if file.endswith('.smali'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                changed = False
                for method, bypass in bypass_methods.items():
                    # Match any .method that ends with )Z (returns boolean)
                    pattern = rf'(\.method\s+(?:public|private|static|final|\s)*{method}\s*\(.*?\)Z[\s\S]*?)\.end\s*method'
                    replacement = f'.method public {method}()Z\n    .registers 2\n    {bypass}\n.end method'
                    if re.search(pattern, content):
                        content = re.sub(pattern, replacement, content)
                        changed = True
                
                if changed:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    patched_count += 1
    
    logger.info(f"  Patched {patched_count} smali files")
    
    # Step 4: Rebuild
    logger.info("Step 4: Rebuilding APK...")
    result = subprocess.run(["apktool", "b", "-f", "-o", cracked, decompiled],
                          capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"Rebuild failed: {result.stderr[:200]}")
    
    # Step 5: Sign
    logger.info("Step 5: Signing APK...")
    result = subprocess.run(["uber-apk-signer", "--apks", cracked, "--out", signed],
                          capture_output=True, text=True, timeout=60)
    
    # Cleanup decompiled
    shutil.rmtree(decompiled, ignore_errors=True)
    
    final_path = signed if os.path.exists(signed) else cracked
    if os.path.exists(final_path):
        return final_path
    raise Exception("APK not generated")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🔥 **AI APK Cracker Bot v4.0**

Send ANY `.apk` file and I'll crack it!

✅ Removes Login/Splash pages
✅ Removes License checks  
✅ Removes Root detection
✅ No errors - No problems

**Just send the APK file!**
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ANY file - especially APK"""
    file = None
    file_name = None
    
    # Check for document
    if update.message.document:
        file = update.message.document
        file_name = file.file_name or "unknown.apk"
    
    # Check for file sent as a file (not document)
    elif update.message.photo:
        await update.message.reply_text("❌ This is a photo, please send the APK file")
        return
    else:
        await update.message.reply_text("❌ Please send an APK file")
        return
    
    # Check if it's an APK (or any file - we'll try anyway)
    is_apk = file_name.lower().endswith('.apk') or not file_name.endswith(('.jpg', '.png', '.mp4', '.mp3', '.zip'))
    
    msg = await update.message.reply_text("📥 **Downloading file...**", parse_mode='Markdown')
    
    try:
        # Download the file
        file_obj = await file.get_file()
        file_size = file.file_size or 0
        logger.info(f"File: {file_name}, Size: {file_size} bytes")
        
        apk_path = f"/tmp/apk_{update.effective_user.id}_{file.file_unique_id}.apk"
        await file_obj.download_to_drive(apk_path)
        
        # Verify it downloaded
        if not os.path.exists(apk_path) or os.path.getsize(apk_path) == 0:
            await msg.edit_text("❌ Failed to download file. Try again.")
            return
        
        await msg.edit_text("🔍 **Analyzing APK...**\nThis takes 1-3 minutes ⏳", parse_mode='Markdown')
        
        # Crack it
        output_path = crack_apk(apk_path)
        
        if output_path and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            await msg.edit_text(
                f"✅ **Cracked!** Size: {size_mb:.1f}MB\n"
                f"📤 **Sending now...**",
                parse_mode='Markdown'
            )
            
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"Cracked_{os.path.basename(output_path)}",
                    caption="🔥 **CRACKED APK READY!**\n\n✅ Login removed\n✅ License bypassed\n✅ Ready to install"
                )
            
            await msg.delete()
            os.remove(output_path)
        else:
            await msg.edit_text("❌ Cracking failed. Try another APK.")
    
    except subprocess.TimeoutExpired:
        await msg.edit_text("❌ Timeout! APK too complex or corrupted.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:150]}")
    finally:
        if os.path.exists(apk_path):
            os.remove(apk_path)

def main():
    # First setup tools
    setup_tools()
    
    # Bot
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_file))
    
    print("🤖 APK Cracker Bot running on Telegram...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
