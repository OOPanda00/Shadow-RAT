
from cryptography.fernet import Fernet, InvalidToken
import os
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import base64
import threading

class DecryptorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Shadow 2026 Decryptor")
        self.root.geometry("620x520")
        self.root.configure(bg="#000000")
        self.root.resizable(False, False)

        tk.Label(root, text="SHADOW 2026 DECRYPTOR", fg="#ff0000", bg="#000000", font=("Arial", 24, "bold")).pack(pady=20)

        tk.Label(root, text="Enter your unique decryption key (base64)", fg="white", bg="#000000", font=("Arial", 12)).pack(pady=10)

        tk.Label(root, text="Decryption Key:", fg="#00ff00", bg="#000000", font=("Consolas", 12)).pack(anchor="w", padx=30)
        self.key_entry = tk.Entry(root, width=60, show="*", font=("Consolas", 12))
        self.key_entry.pack(pady=10, padx=30)

        tk.Button(root, text="Select Encrypted Folder", command=self.select_folder, bg="#ff0000", fg="white", font=("Arial", 12, "bold"), width=35).pack(pady=15)

        self.folder_label = tk.Label(root, text="No folder selected", fg="#888888", bg="#000000", font=("Arial", 10))
        self.folder_label.pack(pady=5)

        self.status = tk.Text(root, height=10, width=70, bg="#111111", fg="#00ff00", font=("Consolas", 10), state="disabled")
        self.status.pack(pady=20, padx=30)

        tk.Button(root, text="START DECRYPTION", command=self.start_decrypt, bg="#00ff00", fg="black", font=("Arial", 14, "bold"), width=35).pack(pady=20)

        self.folder = ""
        self.key = None

    def log(self, msg, color="#00ff00"):
        self.status.configure(state="normal")
        self.status.insert(tk.END, msg + "\n", f"color{color}")
        self.status.tag_config("color#00ff00", foreground="#00ff00")
        self.status.tag_config("color#ff0000", foreground="#ff0000")
        self.status.tag_config("color#ffff00", foreground="#ffff00")
        self.status.see(tk.END)
        self.status.configure(state="disabled")
        self.root.update()

    def select_folder(self):
        self.folder = filedialog.askdirectory(title="Select Folder with .SHADOW files")
        if self.folder:
            self.folder_label.config(text=self.folder, fg="#00ff00")
            self.log(f"Folder selected: {self.folder}")

    def start_decrypt(self):
        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Enter the decryption key")
            return
        if not self.folder:
            messagebox.showerror("Error", "Select the encrypted folder first")
            return

        try:
            self.key = base64.urlsafe_b64decode(key_str)
            Fernet(self.key)  # validate
        except:
            messagebox.showerror("Invalid Key", "Key format invalid or corrupted")
            return

        threading.Thread(target=self.decrypt_folder, daemon=True).start()

    def decrypt_file(self, filepath):
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            fernet = Fernet(self.key)
            decrypted = fernet.decrypt(data)
            original = filepath[:-7] if filepath.endswith(".SHADOW") else filepath + ".decrypted"
            with open(original, "wb") as f:
                f.write(decrypted)
            os.remove(filepath)
            return True
        except InvalidToken:
            return False
        except Exception:
            return False

    def decrypt_folder(self):
        self.log("Decryption started... Do not close the window.", color="#ffff00")
        count = 0
        total = 0
        failed = 0

        for root, _, files in os.walk(self.folder):
            for file in files:
                if file.endswith(".SHADOW"):
                    total += 1
                    fp = os.path.join(root, file)
                    if self.decrypt_file(fp):
                        count += 1
                        if count % 30 == 0:
                            self.log(f"Decrypted {count} files...")
                    else:
                        failed += 1

        if count > 0:
            self.log("\nDECRYPTION FINISHED", color="#00ff00")
            self.log(f"Success: {count} files", color="#00ff00")
            self.log(f"Total processed: {total}", color="#00ff00")
            if failed:
                self.log(f"Failed: {failed} (wrong key / corrupted)", color="#ff0000")
            messagebox.showinfo("Done", f"Decrypted {count} files successfully")
        else:
            self.log("\nNO .SHADOW FILES FOUND OR DECRYPTION FAILED", color="#ff0000")
            messagebox.showerror("Failed", "No encrypted files or invalid key")

if __name__ == "__main__":
    root = tk.Tk()
    app = DecryptorApp(root)
    root.mainloop()
