#!/usr/bin/env python3
"""
artisan_dashboard.py
Simplified post-login dashboard:
 - Login / Signup (MongoDB)
 - Select image (file dialog)
 - Preview image
 - Auto-generate caption + rich description via blip_pipeline.process_single_image()
 - Save upload record under the logged-in user in MongoDB
 - Logout button always visible (top-right)

Place this file in the same folder as `blip_pipeline.py`.
Run: python artisan_dashboard.py
"""

import os
import shutil
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from PIL import Image, ImageTk
from pymongo import MongoClient

# Try to import the blip pipeline function (fallback if missing)
try:
    from blip_pipeline import process_single_image as blip_process_single_image
    BLIP_AVAILABLE = True
except Exception as e:
    BLIP_AVAILABLE = False

    def blip_process_single_image(image_path, thumb_size=(400, 400)):
        """Fallback stub so the GUI remains usable in demos without the model."""
        basename = os.path.basename(image_path)
        caption = f"Placeholder caption for {basename}"
        description = f"Placeholder description for {basename} -- model not loaded."
        return {"image": None, "caption": caption, "description": description}

# -----------------------------
# Configuration & DB
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "artisan_marketplace")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER", "artisan_images")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db["users"]
uploads_collection = db["uploads"]

# Ensure folders exist
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# -----------------------------
# Utility helpers
# -----------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_if_not_exists():
    if not users_collection.find_one({"username": "admin"}):
        users_collection.insert_one({
            "username": "admin",
            "password": hash_password("123456789"),
            "email": "admin@local",
            "is_admin": True,
            "created_at": datetime.utcnow().isoformat()
        })
        print("Admin user created: admin / 123456789")

def save_image_to_project(src_path: str, username: str) -> str:
    """Copy image to project folder and return the new path."""
    ext = os.path.splitext(src_path)[1] or ".jpg"
    safe_user = "".join(c for c in username if c.isalnum() or c in ("_", "-")).strip() or "user"
    ts = int(datetime.utcnow().timestamp() * 1000)
    dest_name = f"{safe_user}_{ts}{ext}"
    dest_path = os.path.join(IMAGE_FOLDER, dest_name)
    shutil.copy2(src_path, dest_path)
    return dest_path

def save_upload_record(user_doc: dict, image_path: str, caption: str, description: str) -> str:
    doc = {
        "user_id": user_doc["_id"],
        "username": user_doc["username"],
        "image_path": image_path,
        "caption": caption,
        "description": description,
        "created_at": datetime.utcnow().isoformat()
    }
    result = uploads_collection.insert_one(doc)
    return str(result.inserted_id)

def load_thumbnail(path: str, size=(320, 320)):
    try:
        img = Image.open(path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# -----------------------------
# GUI: Login -> Dashboard
# -----------------------------
class SimpleArtisanDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Artisan Dashboard")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        # Application state
        self.current_user = None
        create_admin_if_not_exists()

        # Start on login screen
        self.show_login_screen()

    # ---------- common helpers ----------
    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ---------- Login & Signup ----------
    def show_login_screen(self):
        self.clear()

        frame = ttk.Frame(self.root, padding=20)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="Artisan Marketplace", font=("Helvetica", 20, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 12))
        ttk.Label(frame, text="Username:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        username = ttk.Entry(frame, width=30)
        username.grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        password = ttk.Entry(frame, show="*", width=30)
        password.grid(row=2, column=1, sticky="w", pady=6)

        def do_login():
            uname = username.get().strip()
            pwd = password.get().strip()
            if not uname or not pwd:
                messagebox.showwarning("Missing", "Please enter username and password.")
                return
            user = users_collection.find_one({"username": uname})
            if user and user.get("password") == hash_password(pwd):
                self.current_user = user
                self.show_dashboard()
            else:
                messagebox.showerror("Auth Failed", "Invalid username or password.")
                password.delete(0, tk.END)

        def go_signup():
            self.show_signup_screen()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(12,0))
        ttk.Button(btn_frame, text="Login", command=do_login, width=14).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Signup", command=go_signup, width=14).pack(side="left", padx=6)

        ttk.Label(frame, text="(Hint: admin / 123456789)", foreground="gray").grid(row=4, column=0, columnspan=2, pady=(10,0))

    def show_signup_screen(self):
        self.clear()

        frame = ttk.Frame(self.root, padding=16)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="Create Account", font=("Helvetica", 18, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,10))
        ttk.Label(frame, text="Username:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        username = ttk.Entry(frame, width=32)
        username.grid(row=1, column=1, pady=6)
        ttk.Label(frame, text="Email:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        email = ttk.Entry(frame, width=32)
        email.grid(row=2, column=1, pady=6)
        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky="e", padx=6, pady=6)
        password = ttk.Entry(frame, show="*", width=32)
        password.grid(row=3, column=1, pady=6)
        ttk.Label(frame, text="Confirm:").grid(row=4, column=0, sticky="e", padx=6, pady=6)
        confirm = ttk.Entry(frame, show="*", width=32)
        confirm.grid(row=4, column=1, pady=6)

        def do_create():
            uname = username.get().strip()
            mail = email.get().strip()
            pwd = password.get().strip()
            conf = confirm.get().strip()
            if not (uname and mail and pwd and conf):
                messagebox.showwarning("Missing", "Please fill all fields.")
                return
            if pwd != conf:
                messagebox.showerror("Mismatch", "Passwords do not match.")
                return
            if users_collection.find_one({"username": uname}):
                messagebox.showerror("Exists", "Username already exists.")
                return
            users_collection.insert_one({
                "username": uname,
                "password": hash_password(pwd),
                "email": mail,
                "is_admin": False,
                "created_at": datetime.utcnow().isoformat()
            })
            messagebox.showinfo("Created", "Account created. You can now log in.")
            self.show_login_screen()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(12,0))
        ttk.Button(btn_frame, text="Create", command=do_create, width=14).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Back", command=self.show_login_screen, width=14).pack(side="left", padx=6)

    # ---------- Dashboard ----------
    def show_dashboard(self):
        self.clear()

        topbar = ttk.Frame(self.root, padding=(10,8))
        topbar.pack(fill="x")
        title = ttk.Label(topbar, text=f"Artisan Dashboard — Logged in: {self.current_user['username']}", font=("Helvetica", 14, "bold"))
        title.pack(side="left", padx=12)
        logout_btn = ttk.Button(topbar, text="🚪 Logout", command=self.logout)
        logout_btn.pack(side="right", padx=12)

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)

        # Left: upload & preview
        left = ttk.Frame(container, width=420)
        left.pack(side="left", fill="y", padx=(0,12))

        preview_label = ttk.Label(left, text="Preview", font=("Helvetica", 12, "bold"))
        preview_label.pack(anchor="w")
        canvas_frame = ttk.Frame(left, relief="solid", borderwidth=1, width=360, height=360)
        canvas_frame.pack(pady=(8,12))
        canvas_frame.pack_propagate(False)

        img_label = ttk.Label(canvas_frame, text="No image selected", anchor="center")
        img_label.pack(expand=True)

        # Right: generated text + controls
        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        gen_label = ttk.Label(right, text="AI Output", font=("Helvetica", 12, "bold"))
        gen_label.pack(anchor="w")

        caption_var = tk.StringVar(value="")
        ttk.Label(right, text="Caption:", font=("Helvetica", 10, "italic")).pack(anchor="w", pady=(8,0))
        caption_entry = tk.Text(right, height=2, wrap="word")
        caption_entry.pack(fill="x", pady=(2,8))

        ttk.Label(right, text="Rich Description:", font=("Helvetica", 10, "italic")).pack(anchor="w")
        description_entry = tk.Text(right, height=10, wrap="word")
        description_entry.pack(fill="both", expand=True, pady=(2,8))

        status_var = tk.StringVar(value="Ready")

        # Buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill="x", pady=(6,0))
        select_btn = ttk.Button(btn_frame, text="📁 Select Image", width=18)
        select_btn.pack(side="left", padx=6)
        gen_btn = ttk.Button(btn_frame, text="🧠 Generate (Preview)", width=18)
        gen_btn.pack(side="left", padx=6)
        save_db_btn = ttk.Button(btn_frame, text="💾 Save to DB", width=18)
        save_db_btn.pack(side="left", padx=6)

        status_label = ttk.Label(self.root, textvariable=status_var, relief="sunken", anchor="w")
        status_label.pack(side="bottom", fill="x")

        # state
        self.selected_image_path = None
        self.preview_imgtk = None
        self.last_caption = ""
        self.last_description = ""

        # handlers
        def select_image():
            filetypes = [("Image files", "*.jpg *.jpeg *.png *.webp *.avif"), ("All files", "*.*")]
            path = filedialog.askopenfilename(title="Select image", filetypes=filetypes)
            if not path:
                return
            try:
                # copy to project folder so we own it
                dest = save_image_to_project(path, self.current_user["username"])
                self.selected_image_path = dest
                thumb = load_thumbnail(dest, size=(360, 360))
                if thumb:
                    img_label.configure(image=thumb, text="")
                    img_label.image = thumb
                else:
                    img_label.configure(text=os.path.basename(dest))
                    img_label.image = None

                caption_entry.delete("1.0", tk.END)
                description_entry.delete("1.0", tk.END)
                status_var.set(f"Selected {os.path.basename(dest)} — ready to generate")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to select image: {e}")

        def generate_preview():
            if not self.selected_image_path:
                messagebox.showwarning("No image", "Please select an image first.")
                return
            status_var.set("Generating caption — this may take a moment...")
            self.root.update_idletasks()
            try:
                result = blip_process_single_image(self.selected_image_path)
                caption = result.get("caption", "") or ""
                description = result.get("description", "") or caption
                # show them
                caption_entry.delete("1.0", tk.END)
                caption_entry.insert(tk.END, caption)
                description_entry.delete("1.0", tk.END)
                description_entry.insert(tk.END, description)
                self.last_caption = caption
                self.last_description = description
                status_var.set("Generation complete — review then Save to DB")
            except Exception as e:
                status_var.set("Generation failed")
                messagebox.showerror("Generate failed", f"Caption generation failed:\n{e}")

        def save_to_db():
            if not self.selected_image_path:
                messagebox.showwarning("No image", "Please select an image first.")
                return
            caption = caption_entry.get("1.0", tk.END).strip()
            description = description_entry.get("1.0", tk.END).strip()
            if not caption and not description:
                messagebox.showwarning("Empty", "Caption/Description are empty. Generate first or enter text.")
                return
            status_var.set("Saving to database...")
            try:
                inserted_id = save_upload_record(self.current_user, self.selected_image_path, caption, description)
                status_var.set(f"Saved (id={inserted_id})")
                messagebox.showinfo("Saved", "Image and description saved to database.")
            except Exception as e:
                status_var.set("Save failed")
                messagebox.showerror("Save failed", f"Failed to save to DB:\n{e}")

        # wire buttons
        select_btn.configure(command=select_image)
        gen_btn.configure(command=generate_preview)
        save_db_btn.configure(command=save_to_db)

    def logout(self):
        confirm = messagebox.askyesno("Logout", "Are you sure you want to logout?")
        if confirm:
            self.current_user = None
            self.show_login_screen()

# -----------------------------
# Entrypoint
# -----------------------------
def main():
    root = tk.Tk()
    app = SimpleArtisanDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()