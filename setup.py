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

def register_rct(ext=".rcht", prog_name="RachetFile",
                 description="Rachet Source File",
                 icon_path=None, launcher=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))

    if icon_path is None:
        icon_path = os.path.join(base_dir, "rachet.ico")
    if launcher is None:
        launcher = os.path.join(base_dir, "compiler.exe")  # your executable

    # Absolute paths
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

    # Open command
    with winreg.CreateKey(root, f"{classes}\\{prog_name}\\Shell\\Open\\Command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{launcher}" "%1"')

    print("[+] .rcht files registered with custom icon and launcher.")

def restart_explorer():
    """Restart Windows Explorer to refresh icons."""
    print("[*] Restarting Explorer to refresh icons...")
    subprocess.run("taskkill /IM explorer.exe /F", shell=True)
    time.sleep(1)
    subprocess.run("start explorer.exe", shell=True)
    print("[+] Explorer restarted. Icons should update immediately.")
    print("[*] For the description to update, you may need to log out and back in.")

if __name__ == "__main__":
    print("[*] Clearing old .rcht registry entries...")
    delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\.rcht")
    delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\RachetFile")
    
    print("[*] Registering .rcht file type...")
    register_rct()
    
    restart_explorer()
    print("[*] Done! Your .rcht files should now show the icon and open with compiler.exe.")
    print("[*] If the description still shows 'Resource Compiler Template', log out and log back in.")
