import os

folder = "artisan_images"
supported_exts = (".jpg", ".jpeg", ".png", ".webp")

# Sequentially rename images: img1.jpg, img2.jpg, ...
count = 1
for filename in sorted(os.listdir(folder)):
    if filename.lower().endswith(supported_exts):
        ext = os.path.splitext(filename)[1]  # keep original extension
        new_name = f"img{count}{ext}"
        old_path = os.path.join(folder, filename)
        new_path = os.path.join(folder, new_name)
        os.rename(old_path, new_path)
        print(f"Renamed {filename} -> {new_name}")
        count += 1