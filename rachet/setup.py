import os
import subprocess
import time
import winreg

def delete_key_recursive(root, key_path):
    """Recursively delete a registry key and all its subkeys."""
    try:
        with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    subkey = winreg.EnumKey(key, 0)  # always delete first subkey
                    delete_key_recursive(root, f"{key_path}\\{subkey}")
                except OSError:
                    break
        winreg.DeleteKey(root, key_path)
        print(f"[+] Deleted key: {key_path}")
    except FileNotFoundError:
        pass

def register_rct(ext, prog_name, description, icon_path, launcher):
    """Register a file type with the given extension, icon, and launcher exe."""
    icon_path = os.path.abspath(icon_path)
    launcher = os.path.abspath(launcher)

    root = winreg.HKEY_CURRENT_USER
    classes = r"Software\Classes"

    # Delete old keys
    delete_key_recursive(root, f"{classes}\\{ext}")
    delete_key_recursive(root, f"{classes}\\{prog_name}")

    # Associate extension with ProgID
    with winreg.CreateKey(root, f"{classes}\\{ext}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, prog_name)
        winreg.SetValueEx(key, "PerceivedType", 0, winreg.REG_SZ, "text")

    # ProgID description
    with winreg.CreateKey(root, f"{classes}\\{prog_name}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, description)

    # Default icon
    with winreg.CreateKey(root, f"{classes}\\{prog_name}\\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)

    # Open command → run compiler.exe
    with winreg.CreateKey(root, f"{classes}\\{prog_name}\\Shell\\Open\\Command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{launcher}" "%1"')

    print(f"[+] {ext} files registered with custom icon and launcher.")

def add_to_path_permanent():
    """Add current script directory to PATH permanently (user-level)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_key = r"Environment"
    root = winreg.HKEY_CURRENT_USER

    with winreg.OpenKey(root, env_key, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""

        if base_dir not in current_path:
            new_path = current_path + ";" + base_dir if current_path else base_dir
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"[+] Added {base_dir} to PATH permanently.")
        else:
            print("[*] Directory already in PATH.")

def create_gears_launcher():
    """Create a gears.bat file in the same dir so 'gears' can be called anywhere."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "gears.py")
    bat_path = os.path.join(base_dir, "gears.bat")

    with open(bat_path, "w") as f:
        f.write(f'@echo off\npython "{script_path}" %*\n')

    print(f"[+] Created launcher: {bat_path} (callable as 'gears')")

def restart_explorer():
    """Restart Windows Explorer to refresh icons."""
    print("[*] Restarting Explorer to refresh icons...")
    subprocess.run("taskkill /IM explorer.exe /F", shell=True)
    time.sleep(1)
    subprocess.run("start explorer.exe", shell=True)
    print("[+] Explorer restarted. Icons should update immediately.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    compiler_exe = os.path.join(base_dir, "compiler.exe")

    print("[*] Clearing old registry entries...")
    delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\.rx")
    delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\RachetFile")
    delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\.rxc")
    delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\RachetCompressedFile")

    print("[*] Registering .rx file type...")
    register_rct(
        ext=".rx",
        prog_name="RachetFile",
        description="Rachet Source File",
        icon_path=os.path.join(base_dir, "rachet.ico"),
        launcher=compiler_exe
    )

    print("[*] Registering .rxc file type...")
    register_rct(
        ext=".rxc",
        prog_name="RachetCompressedFile",
        description="Rachet Compressed File",
        icon_path=os.path.join(base_dir, "rachet_compressed.ico"),
        launcher=compiler_exe
    )

    add_to_path_permanent()
    create_gears_launcher()
    restart_explorer()

    print("[*] Done! .rx and .rxc now open with compiler.exe, and 'gears' can be called from anywhere.")
