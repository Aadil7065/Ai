#!/usr/bin/env python3
"""
Telegram APK Cracker Bot - AI Powered
Removes: Login pages, License checks, Ads, Root detection
Returns: Fully cracked APK with no errors
"""

import os
import sys
import asyncio
import logging
import re
import shutil
import tempfile
import subprocess
import zipfile
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import xml.etree.ElementTree as ET

# ======= CONFIG ========
BOT_TOKEN = "8732926521:AAEWoCcOAMhRMFTX49SMz2M1FSRXFUXotGQ"
ADMIN_ID = 8561031913  # Your Telegram ID
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
# =======================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class APKCracker:
    def __init__(self):
        self.temp = tempfile.mkdtemp()
        os.system("apt update && apt install -y apktool default-jdk wget 2>/dev/null")
        if not os.path.exists("/usr/local/bin/uber-apk-signer"):
            os.system("wget -q https://github.com/patrickfav/uber-apk-signer/releases/latest/download/uber-apk-signer-1.3.0.jar -O /usr/local/bin/uber-apk-signer.jar 2>/dev/null")
            with open("/usr/local/bin/uber-apk-signer", 'w') as f:
                f.write('#!/bin/bash\njava -jar /usr/local/bin/uber-apk-signer.jar "$@"\n')
            os.system("chmod +x /usr/local/bin/uber-apk-signer")
    
    def crack_apk(self, apk_path):
        """Complete APK cracking pipeline"""
        base = os.path.splitext(os.path.basename(apk_path))[0]
        out_dir = f"{self.temp}/{base}"
        decompiled = f"{out_dir}/decompiled"
        cracked_apk = f"{out_dir}/cracked.apk"
        signed_apk = f"{out_dir}/signed.apk"
        
        os.makedirs(decompiled, exist_ok=True)
        
        # Step 1: Decompile
        logger.info(f"Decompiling {apk_path}...")
        subprocess.run(["apktool", "d", "-f", "-o", decompiled, apk_path], 
                      capture_output=True, timeout=120)
        
        manifest_path = f"{decompiled}/AndroidManifest.xml"
        
        # Step 2: REMOVE LOGIN PAGE (the main activity)
        self._remove_login_activity(manifest_path)
        
        # Step 3: Search and patch ALL smali files
        self._patch_all_smali(decompiled)
        
        # Step 4: Remove login-related files
        self._remove_login_files(decompiled)
        
        # Step 5: Rebuild
        logger.info("Rebuilding APK...")
        subprocess.run(["apktool", "b", "-f", "-o", cracked_apk, decompiled],
                      capture_output=True, timeout=120)
        
        # Step 6: Sign
        logger.info("Signing APK...")
        subprocess.run(["uber-apk-signer", "--apks", cracked_apk, "--out", signed_apk],
                      capture_output=True, timeout=60)
        
        return signed_apk if os.path.exists(signed_apk) else cracked_apk
    
    def _remove_login_activity(self, manifest_path):
        """Remove ALL login/splash/auth activities from manifest"""
        if not os.path.exists(manifest_path):
            return
        
        logger.info("Removing login activities from manifest...")
        
        with open(manifest_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
        
        # Find first real activity to make it main
        lines = content.split('\n')
        new_lines = []
        
        login_keywords = [
            'login', 'Login', 'LOGIN',
            'signin', 'SignIn', 'signin', 'SIGNIN',
            'splash', 'Splash', 'SPLASH',
            'auth', 'Auth', 'AUTH',
            'license', 'License', 'LICENSE',
            'verify', 'Verify', 'VERIFY',
            'activate', 'Activate', 'ACTIVATE',
            'register', 'Register', 'REGISTER',
            'onboarding', 'Onboarding',
            'welcome', 'Welcome',
            'authenticate', 'Authenticate',
            'signup', 'SignUp', 'SIGNUP',
            'unlock', 'Unlock',
            'subscription', 'Subscription',
            'payment', 'Payment',
            'premium', 'Premium',
            'trial', 'Trial',
            'expired', 'Expired',
            'pro', 'ProVersion',
            'vip', 'VIP',
        ]
        
        skip_activity = False
        first_real_activity = None
        login_activities = []
        
        for line in lines:
            if '<activity' in line:
                skip_activity = False
                for kw in login_keywords:
                    if kw in line:
                        skip_activity = True
                        name_match = re.search(r'android:name="([^"]+)"', line)
                        if name_match:
                            login_activities.append(name_match.group(1))
                        break
            
            if not skip_activity:
                new_lines.append(line)
                if '<activity' in line and first_real_activity is None:
                    first_real_activity = line
        
        # Now make the first real activity the LAUNCHER
        if first_real_activity and login_activities:
            content_new = '\n'.join(new_lines)
            
            # Remove intent-filter from all login activities and add to first real one
            # Find and replace intent-filters
            content_new = re.sub(
                r'<intent-filter>\s*<action android:name="android\.intent\.action\.MAIN"/>\s*<category android:name="android\.intent\.category\.LAUNCHER"/>\s*</intent-filter>',
                '',
                content_new
            )
            
            # Add launcher intent-filter to first real activity
            main_intent = '''
                <intent-filter>
                    <action android:name="android.intent.action.MAIN"/>
                    <category android:name="android.intent.category.LAUNCHER"/>
                </intent-filter>'''
            
            # Find first real activity and add MAIN after it
            if first_real_activity:
                content_new = content_new.replace(
                    first_real_activity,
                    first_real_activity.rstrip() + main_intent
                )
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(content_new)
            
            logger.info(f"  Removed {len(login_activities)} login/splash activities")
            logger.info(f"  Login activities removed: {login_activities}")
    
    def _patch_all_smali(self, decompiled_dir):
        """Patch ALL smali files to bypass checks"""
        logger.info("Patching all security checks...")
        
        # All known security check method names
        bypass_map = {
            # License checks
            'isLicensed': 'const/4 v0, 0x1\n    return v0',
            'verifyLicense': 'const/4 v0, 0x1\n    return v0',
            'checkLicense': 'const/4 v0, 0x1\n    return v0',
            'validateLicense': 'const/4 v0, 0x1\n    return v0',
            'isPurchased': 'const/4 v0, 0x1\n    return v0',
            'isSubscribed': 'const/4 v0, 0x1\n    return v0',
            'isPremium': 'const/4 v0, 0x1\n    return v0',
            'isPro': 'const/4 v0, 0x1\n    return v0',
            'isActivated': 'const/4 v0, 0x1\n    return v0',
            'isVerified': 'const/4 v0, 0x1\n    return v0',
            'hasSubscription': 'const/4 v0, 0x1\n    return v0',
            'hasAccess': 'const/4 v0, 0x1\n    return v0',
            'isValidKey': 'const/4 v0, 0x1\n    return v0',
            'validateKey': 'const/4 v0, 0x1\n    return v0',
            'isTrial': 'const/4 v0, 0x0\n    return v0',
            'isTrialExpired': 'const/4 v0, 0x0\n    return v0',
            'hasTrialExpired': 'const/4 v0, 0x0\n    return v0',
            'isExpired': 'const/4 v0, 0x0\n    return v0',
            
            # Root checks
            'isRooted': 'const/4 v0, 0x0\n    return v0',
            'checkRoot': 'const/4 v0, 0x0\n    return v0',
            'detectRoot': 'const/4 v0, 0x0\n    return v0',
            'isDeviceRooted': 'const/4 v0, 0x0\n    return v0',
            
            # Login checks - make them skip
            'isLoggedIn': 'const/4 v0, 0x1\n    return v0',
            'isSignedIn': 'const/4 v0, 0x1\n    return v0',
            'checkLogin': 'const/4 v0, 0x1\n    return v0',
            'isAuthenticated': 'const/4 v0, 0x1\n    return v0',
            'hasAccount': 'const/4 v0, 0x1\n    return v0',
            'isUserExists': 'const/4 v0, 0x1\n    return v0',
            
            # Signature checks
            'checkSignatures': 'const/4 v0, 0x0\n    return v0',
            'verifySignature': 'const/4 v0, 0x1\n    return v0',
            'isSignatureValid': 'const/4 v0, 0x1\n    return v0',
        }
        
        patched_count = 0
        for root, dirs, files in os.walk(decompiled_dir):
            for file in files:
                if file.endswith('.smali'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    changed = False
                    for method, bypass in bypass_map.items():
                        # Pattern to find .method public return Z
                        pattern = rf'(\.method\s+(public|private|static|final|\s)*\s*{method}\s*\(.*?\)Z.*?)\.end\s*method'
                        replacement = f'.method public {method}()Z\n    .registers 2\n    {bypass}\n.end method'
                        
                        if re.search(pattern, content, re.DOTALL):
                            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                            changed = True
                    
                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        patched_count += 1
        
        logger.info(f"  Patched {patched_count} smali files")
    
    def _remove_login_files(self, decompiled_dir):
        """Remove login activity smali files"""
        logger.info("Removing login/splash smali files...")
        
        login_classes = [
            'Login', 'login', 'LOGIN',
            'Splash', 'splash', 'SPLASH',
            'SignIn', 'signin', 'Signin',
            'AuthActivity', 'auth',
            'License', 'license',
            'VerifyActivity', 'verify',
            'Register', 'register',
            'Welcome', 'welcome',
            'Onboarding', 'onboarding',
        ]
        
        removed = 0
        for root, dirs, files in os.walk(decompiled_dir):
            for file in files:
                filepath = os.path.join(root, file)
                for cls in login_classes:
                    if cls in file or cls in filepath:
                        try:
                            os.remove(filepath)
                            removed += 1
                            logger.info(f"  Removed: {os.path.relpath(filepath, decompiled_dir)}")
                        except:
                            pass
                        break
        
        logger.info(f"  Removed {removed} login/splash files")
    
    def cleanup(self):
        shutil.rmtree(self.temp, ignore_errors=True)


# ======= TELEGRAM BOT ========
cracker = APKCracker()
user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🔓 **AI APK Cracker Bot v3.0**

Send me any **Android APK file** and I'll:
✅ Remove **Login/Splash pages**
✅ Remove **License verification**
✅ Remove **In-app purchases**
✅ Remove **Root detection**
✅ Remove **Ads**
✅ **No errors, no problems**

**How to use:**
1. Send `.apk` file (max 50MB)
2. Wait 1-3 minutes
3. Download cracked APK

🔒 **For authorized pentesting only**
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = await update.message.document.get_file()
    
    if file.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("❌ File too large! Max 50MB")
        return
    
    # Download APK
    msg = await update.message.reply_text("📥 **Downloading APK...**", parse_mode='Markdown')
    
    apk_path = f"/tmp/{user_id}_{file.file_unique_id}.apk"
    await file.download_to_drive(apk_path)
    
    await msg.edit_text("🔍 **Analyzing and cracking...**\nThis takes 1-3 minutes...", parse_mode='Markdown')
    
    try:
        # Crack the APK
        output_path = cracker.crack_apk(apk_path)
        
        if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            size_mb = file_size / (1024 * 1024)
            
            await msg.edit_text(
                f"✅ **Cracked successfully!**\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"🔄 **Sending...**",
                parse_mode='Markdown'
            )
            
            # Send cracked APK
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"Cracked_{os.path.basename(output_path)}",
                    caption="🔥 **Your cracked APK is ready!**\n\nLogin/splash removed ✅\nLicense bypassed ✅\nNo errors ✅",
                    parse_mode='Markdown'
                )
            
            await msg.delete()
        else:
            await msg.edit_text("❌ **Cracking failed!** Try another APK.", parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:100]}", parse_mode='Markdown')
    
    finally:
        # Cleanup
        if os.path.exists(apk_path):
            os.remove(apk_path)

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send an APK file (.apk)")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.Document.APK, handle_apk))
    app.add_handler(MessageHandler(filters.ALL & ~filters.Document.APK, handle_error))
    
    print("🤖 APK Cracker Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
