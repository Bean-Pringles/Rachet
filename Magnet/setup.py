#!/usr/bin/env python3
"""
Windows Registry Setup for Magnet (.mgn) Files
This script registers .mgn files with Windows and associates them with magnet.exe
Requires administrator privileges to run
"""

import winreg
import os
import sys
import ctypes

def is_admin():
    """Check if the script is running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    """Request administrator privileges and restart the script"""
    if sys.platform == 'win32':
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )

def get_script_directory():
    """Get the directory where this script is located"""
    return os.path.dirname(os.path.abspath(__file__))

def register_mgn_extension(exe_path, icon_path):
    """
    Register .mgn file extension with Windows
    
    Args:
        exe_path: Full path to magnet.exe
        icon_path: Full path to magnet.ico
    """
    try:
        # Create or open the .mgn extension key
        key_extension = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".mgn")
        winreg.SetValueEx(key_extension, "", 0, winreg.REG_SZ, "MagnetFile")
        winreg.SetValueEx(key_extension, "Content Type", 0, winreg.REG_SZ, "application/x-magnet")
        winreg.CloseKey(key_extension)
        print("Registered .mgn extension")

        # Create or open the MagnetFile type key
        key_filetype = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "MagnetFile")
        winreg.SetValueEx(key_filetype, "", 0, winreg.REG_SZ, "Magnet File")
        winreg.CloseKey(key_filetype)
        print("Created MagnetFile type")

        # Set the default icon
        if os.path.exists(icon_path):
            key_icon = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"MagnetFile\DefaultIcon")
            winreg.SetValueEx(key_icon, "", 0, winreg.REG_SZ, icon_path)
            winreg.CloseKey(key_icon)
            print(f"Set icon: {icon_path}")
        else:
            print(f"⚠ Warning: Icon file not found at {icon_path}")
            # Use the exe as icon source if ico doesn't exist
            key_icon = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"MagnetFile\DefaultIcon")
            winreg.SetValueEx(key_icon, "", 0, winreg.REG_SZ, f"{exe_path},0")
            winreg.CloseKey(key_icon)
            print(f"Using exe icon: {exe_path}")

        # Set the command to open .mgn files
        key_command = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"MagnetFile\shell\open\command")
        winreg.SetValueEx(key_command, "", 0, winreg.REG_SZ, f'"{exe_path}" "%1"')
        winreg.CloseKey(key_command)
        print(f"Associated with: {exe_path}")

        # Add "Edit" verb (optional - opens in notepad for debugging)
        key_edit = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"MagnetFile\shell\edit\command")
        winreg.SetValueEx(key_edit, "", 0, winreg.REG_SZ, 'notepad.exe "%1"')
        winreg.CloseKey(key_edit)
        print("Added 'Edit' option to context menu")

        print("\nSuccessfully registered .mgn files with Windows!")
        print("You can now double-click .mgn files to open them with Magnet.")
        
        # Notify Windows to refresh file associations
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        print("Refreshed Windows file associations")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def unregister_mgn_extension():
    """Remove .mgn file association from Windows"""
    try:
        # Delete .mgn extension key
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, ".mgn")
            print("Removed .mgn extension")
        except FileNotFoundError:
            print(".mgn extension was not registered")

        # Delete MagnetFile type keys recursively
        def delete_key_recursively(root, path):
            try:
                key = winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS)
                subkeys = []
                try:
                    i = 0
                    while True:
                        subkeys.append(winreg.EnumKey(key, i))
                        i += 1
                except OSError:
                    pass
                
                for subkey in subkeys:
                    delete_key_recursively(root, f"{path}\\{subkey}")
                
                winreg.CloseKey(key)
                winreg.DeleteKey(root, path)
            except FileNotFoundError:
                pass

        delete_key_recursively(winreg.HKEY_CLASSES_ROOT, "MagnetFile")
        print("Removed MagnetFile type")

        print("\n Successfully unregistered .mgn files from Windows!")
        
        # Notify Windows to refresh
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Magnet File Association Setup")
    print("=" * 60)
    
    # Check for admin privileges
    if not is_admin():
        print("\n⚠ This script requires administrator privileges.")
        print("Requesting elevation...")
        request_admin()
        sys.exit()
    
    # Get paths
    script_dir = get_script_directory()
    exe_path = os.path.join(script_dir, "magnet.exe")
    icon_path = os.path.join(script_dir, "magnet.ico")
    
    # Show menu
    print(f"\nScript directory: {script_dir}")
    print(f"Magnet.exe path: {exe_path}")
    print(f"Icon path: {icon_path}")
    print()
    
    if not os.path.exists(exe_path):
        print(f"Error: magnet.exe not found at {exe_path}")
        print("Please make sure magnet.exe is in the same directory as this script.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("What would you like to do?")
    print("1. Register .mgn files (Install)")
    print("2. Unregister .mgn files (Uninstall)")
    print("3. Exit")
    print()
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        print("\n" + "=" * 60)
        print("Installing file association...")
        print("=" * 60 + "\n")
        success = register_mgn_extension(exe_path, icon_path)
        if success:
            print("\n🎉 Installation complete!")
    elif choice == "2":
        print("\n" + "=" * 60)
        print("Uninstalling file association...")
        print("=" * 60 + "\n")
        success = unregister_mgn_extension()
        if success:
            print("\n Uninstallation complete!")
    elif choice == "3":
        print("Exiting...")
        sys.exit(0)
    else:
        print("Invalid choice.")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()