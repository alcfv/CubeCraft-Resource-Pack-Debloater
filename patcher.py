"""
Minecraft Bedrock Resource-Pack Patcher (UWP + GDK)
- Choose version (UWP or GDK)
- Choose one of 3 patch options (each zip contains 5 resource-pack folders)
- Option to clear the packcache/resource folder (makes a backup first)
- Creates a timestamped backup before any destructive action
- Downloads chosen ZIP, extracts, and copies each top-level folder into the target
"""

import os
import shutil
import zipfile
import requests
import tempfile
from datetime import datetime

# ------------------ CONFIG ------------------
PATCHES = {
    "1": {
        "name": "Java Animations Fix + Debloat (removes some lobby cosmetics functionality)",
        "url": "https://github.com/alcfv/patch-file-host/releases/download/V1/Java.Anims.Fix.+.Debloat.zip"
    },
    "2": {
        "name": "Java Animations Armor Overlay Fix",
        "url": "https://github.com/alcfv/patch-file-host/releases/download/V1/Java.Anims.Armor.Fix.zip"
    },
    "3": {
        "name": "Java Animations Armor Overlay + Running Animation Fix (may hide lobby costumes)",
        "url": "https://github.com/alcfv/patch-file-host/releases/download/V1/Java.Anims.Armor.Run.Fix.zip"
    }
}

PATH_UWP = r"%localappdata%\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalCache\minecraftpe\packcache\resource"
PATH_GDK = r"%temp%\minecraftpe\packcache\resource"
# --------------------------------------------

def expand(p):
    return os.path.expandvars(p)

def now_stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def prompt_version():
    print("=======================================")
    print("   Minecraft Resource Pack Patcher")
    print("=======================================")
    print("Choose your Minecraft installation type:")
    print("  1) Minecraft Bedrock BEFORE 1.21.20 (UWP)")
    print("  2) Minecraft Bedrock 1.21.20+ (GDK)")
    v = input("Enter 1 or 2: ").strip()
    if v == "1":
        return expand(PATH_UWP)
    elif v == "2":
        return expand(PATH_GDK)
    else:
        print("Invalid selection. Exiting.")
        exit(1)

def prompt_action():
    print("\nSelect a patch action:")
    for k in sorted(PATCHES.keys()):
        print(f"  {k}) {PATCHES[k]['name']}")
    print("  4) Clear patched files (backup then clear packcache/resource)")
    choice = input("\nEnter 1, 2, 3 or 4: ").strip()
    if choice in ("1","2","3","4"):
        return choice
    else:
        print("Invalid selection. Exiting.")
        exit(1)

def make_backup(folder):
    if not os.path.exists(folder):
        print("Target folder does not exist; skipping backup.")
        return None
    parent = os.path.dirname(folder.rstrip("/\\"))
    base = os.path.basename(folder.rstrip("/\\"))
    backup_name = f"{base}_backup_{now_stamp()}"
    backup_path = os.path.join(parent, backup_name)
    print(f"\nCreating backup: {backup_path}")
    shutil.copytree(folder, backup_path)
    print("Backup complete.")
    return backup_path

def clear_folder_contents(folder):
    if not os.path.exists(folder):
        print("Target folder does not exist — creating it.")
        os.makedirs(folder, exist_ok=True)
        return
    print("\nClearing folder contents...")
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception as e:
            print("  WARNING: failed to remove", path, "->", e)
    print("Folder cleared.")

def download_zip(url, dest_path):
    print("\nDownloading patch from:", url)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = r.headers.get("content-length")
        total = int(total) if total and total.isdigit() else None
        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  downloaded {downloaded}/{total} bytes ({pct}%)", end="", flush=True)
    if total:
        print("\r  downloaded {}/{} bytes (100%)".format(downloaded, total))
    else:
        print("  download complete.")
    return dest_path

def extract_zip(zip_path, dest_dir):
    print("\nExtracting zip...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)
    print("Extracted to:", dest_dir)
    return dest_dir

def copy_top_level_folders(src_root, dst_root):
    applied = []
    for name in os.listdir(src_root):
        src = os.path.join(src_root, name)
        dst = os.path.join(dst_root, name)
        if os.path.isdir(src):
            if os.path.exists(dst):
                try:
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                except Exception as e:
                    print("  WARNING: failed to remove existing", dst, "->", e)
            shutil.copytree(src, dst)
            applied.append(name)
            print("  Copied pack:", name)
        else:
            try:
                shutil.copy2(src, dst)
                print("  Copied file:", name)
            except Exception:
                print("  Skipped non-dir item:", name)
    return applied

def main():
    target = prompt_version()
    print("\nTarget folder:", target)
    action = prompt_action()

    if not os.path.exists(target):
        print("\nTarget folder does not exist. Creating it now.")
        os.makedirs(target, exist_ok=True)

    if action == "4":
        print("\nClearing patched files...")
        backup = make_backup(target)
        clear_folder_contents(target)
        print("\nCleared. Game will redownload server packs when you join servers.")
        if backup:
            print("Backup located at:", backup)
        input("\nPress ENTER to exit.")
        return

    patch = PATCHES.get(action)
    if not patch:
        print("Invalid patch selection. Exiting.")
        return

    print(f"\nApplying patch: {patch['name']}")

    backup = make_backup(target)
    clear_folder_contents(target)

    tmpdir = tempfile.mkdtemp(prefix="patcher_")
    zip_path = os.path.join(tmpdir, "patch.zip")
    try:
        download_zip(patch["url"], zip_path)
        extract_dir = os.path.join(tmpdir, "extracted")
        extract_zip(zip_path, extract_dir)

        applied = copy_top_level_folders(extract_dir, target)
        print("\nApplied packs count:", len(applied))
        if backup:
            print("Backup available at:", backup)
        print("\nPatch applied successfully!")
    except Exception as e:
        print("ERROR during patch application:", e)
        if backup:
            print("You can restore from backup at:", backup)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    input("\nPress ENTER to exit.")

if __name__ == "__main__":
    main()
