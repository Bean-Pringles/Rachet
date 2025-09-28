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
    """Add current script directory to PATH permanently (user-level) and refresh current session."""
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
            
            # Refresh PATH in current session
            refresh_current_path()
        else:
            print("[*] Directory already in PATH.")

def refresh_current_path():
    """Refresh the PATH environment variable in the current Python session."""
    try:
        # Get user PATH
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                user_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                user_path = ""
        
        # Get system PATH
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            try:
                system_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                system_path = ""
        
        # Combine and update current session
        combined_path = user_path + ";" + system_path if user_path and system_path else user_path or system_path
        os.environ["PATH"] = combined_path
        
        print("[+] PATH refreshed in current session. 'gears' command should now work immediately.")
        
    except Exception as e:
        print(f"[!] Could not refresh PATH in current session: {e}")
        print("[*] You may need to restart your terminal or run:")
        print('    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")')

def create_gears_script():
    """Create the main gears.py script that handles compile and fetch commands."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gears_script = os.path.join(base_dir, "gears.py")
    
    gears_content = '''import os
import sys
import subprocess

def to_wsl_path(win_path: str) -> str:
    """
    Convert a Windows path like C:\\\\Users\\\\you\\\\file.py
    to a WSL path like /mnt/c/Users/you/file.py
    """
    drive, path = os.path.splitdrive(win_path)
    # replace backslashes with forward slashes
    return f"/mnt/{drive[0].lower()}{path.replace('\\\\', '/')}"

def compile_rachet_file(file_path):
    """Compile a .rx file using WSL."""
    # Resolve to absolute path
    program_path = os.path.abspath(file_path)
    
    # Check if file exists
    if not os.path.exists(program_path):
        print(f"Error: File '{file_path}' not found.")
        return 1
    
    # Check if it's a .rx file
    if not program_path.endswith('.rx'):
        print(f"Error: File '{file_path}' is not a .rx file.")
        return 1
    
    # Directory of the target program
    program_dir = os.path.dirname(program_path)
    program_name = os.path.basename(program_path)
    
    # Find compiler.py (assumes it lives in rachet/ under this script's directory)
    this_script_path = os.path.abspath(__file__)
    this_dir = os.path.dirname(this_script_path)
    compiler_path = os.path.join(this_dir, "rachet", "compiler.py")
    
    # Check if compiler exists
    if not os.path.exists(compiler_path):
        print(f"Error: Compiler not found at '{compiler_path}'")
        print("Make sure the rachet/compiler.py file exists in the gears directory.")
        return 1
    
    # Convert paths to WSL format
    compiler_path_wsl = to_wsl_path(compiler_path)
    program_dir_wsl = to_wsl_path(program_dir)
    
    print(f"[*] Compiling {program_name}...")
    
    # Run inside WSL in the program's directory
    # Using bash -ic so PATH and tools like xorriso work
    cmd = f"cd '{program_dir_wsl}' && python3 '{compiler_path_wsl}' '{program_name}'"
    
    try:
        result = subprocess.run(
            ["wsl", "bash", "-ic", cmd],
            capture_output=True,
            text=True
        )
        
        # Output from the compiler
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr, file=sys.stderr)
        
        return result.returncode
        
    except FileNotFoundError:
        print("Error: WSL not found. Make sure Windows Subsystem for Linux is installed.")
        return 1
    except Exception as e:
        print(f"Error running compiler: {e}")
        return 1

def show_rachet_info():
    """Display Rachet ASCII art and information."""
    # REPLACE THIS SECTION WITH YOUR ASCII ART                                
    print ("""
                                       .:^^^.         |   Rachet is a compiler               
                                    :75GB##5^         |   based programming laungue         
                                  .?B####P~           |   designed for easy OS Dev        
                                 .5####B7         .:  |   by students.      
                                 !######7        !GP. |        
                      .:^~~!777!.7#######7..   ^5##B: |   It was made by Bean Pringles            
                  .^!JY5PPPPB&&&?^B#######BGPY5####5  |   in a hopes that students will         
                .!Y5PP5YJ?7!7?J!7G################5:  |   learn all about computers.           
               ~YPPPY7^.      !P###############BP7    |              
             .?P55Y~        !P#########BYJYYY?!^      |   Have fun, and let's see what       
             ?P55J.       ~5##########Y~?PP?          |   you can make.          
            ^5555:      ^J5PPB######5^ :####~         |             
            !P5P?     ^J555555PB##5~    5###?         |   Good Luck, and may the           
            !P5P?   ^J5555555555J~      5###?         |   compiler be nice to you,           
            ^55PJ.^?55555555P5J^       :B###~         |              
           ..!7!~?5P55555555J^        .P###Y          |   - Bean_Pringles >:D           
       .~?JY5YYY5P5555555PJ~         !G###5.          |   (https://github.com/Bean-Pringles)         
      !YPP5555555555555PJ^        :7P###B?            |              
    .?P55P5PPPP5555555Y~!?7!!!7?YPB#&#BJ:             |              
    ~P5P57^~!7?5555555?.B&&&&&&&&#BGY!.               |              
    !P57:      !5555555.~?JYYYY?7~:.                  |              
    :?:         ?P555PJ                               |              
              .!Y555PY:                               |              
            .~YPPP5Y7.                                |              
            !JJJ?!^.                                  |
       
""")

def show_help():
    """Show help information."""
    print("Gears - Rachet Language Toolchain")
    print("")
    print("Usage:")
    print("  gears compile <file.rx>    Compile a Rachet source file")
    print("  gears fetch                Show Rachet information and ASCII art")
    print("  gears help                 Show this help message")
    print("")
    print("Examples:")
    print("  gears compile main.rx")
    print("  gears compile src/hello.rx")
    print("  gears fetch")

def main():
    if len(sys.argv) < 2:
        show_help()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "compile":
        if len(sys.argv) < 3:
            print("Error: No file specified for compilation.")
            print("Usage: gears compile <file.rx>")
            return 1
        
        file_path = sys.argv[2]
        return compile_rachet_file(file_path)
    
    elif command == "fetch":
        show_rachet_info()
        return 0
    
    elif command == "help" or command == "--help" or command == "-h":
        show_help()
        return 0
    
    else:
        print(f"Error: Unknown command '{command}'")
        show_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    with open(gears_script, "w") as f:
        f.write(gears_content)
    
    print(f"[+] Created gears.py script at {gears_script}")

def create_gears_launcher():
    """Create a gears.bat file in the same dir so 'gears' can be called anywhere."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gears_script = os.path.join(base_dir, "gears.py")
    bat_path = os.path.join(base_dir, "gears.bat")

    with open(bat_path, "w") as f:
        f.write(f'@echo off\npython "{gears_script}" %*\n')

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
    create_gears_script()
    create_gears_launcher()
    restart_explorer()

    print("[*] Done! .rx and .rxc now open with compiler.exe, and 'gears' can be called from anywhere.")
    print("[*] You can now use:")
    print("    gears compile main.rx")
    print("    gears fetch")
    print("    gears help")