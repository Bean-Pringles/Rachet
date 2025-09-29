import os
import subprocess
import time
import sys
import shutil
import stat

# Detect platform
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

if IS_WINDOWS:
    import winreg

def delete_key_recursive(root, key_path):
    """Recursively delete a registry key and all its subkeys (Windows only)."""
    if not IS_WINDOWS:
        return
    
    try:
        with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    subkey = winreg.EnumKey(key, 0)
                    delete_key_recursive(root, f"{key_path}\\{subkey}")
                except OSError:
                    break
        winreg.DeleteKey(root, key_path)
        print(f"[+] Deleted key: {key_path}")
    except FileNotFoundError:
        pass

def register_rct(ext, prog_name, description, icon_path, launcher):
    """Register a file type with the given extension, icon, and launcher (Windows only)."""
    if not IS_WINDOWS:
        return
    
    icon_path = os.path.abspath(icon_path)
    launcher = os.path.abspath(launcher)

    root = winreg.HKEY_CURRENT_USER
    classes = r"Software\Classes"

    delete_key_recursive(root, f"{classes}\\{ext}")
    delete_key_recursive(root, f"{classes}\\{prog_name}")

    with winreg.CreateKey(root, f"{classes}\\{ext}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, prog_name)
        winreg.SetValueEx(key, "PerceivedType", 0, winreg.REG_SZ, "text")

    with winreg.CreateKey(root, f"{classes}\\{prog_name}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, description)

    with winreg.CreateKey(root, f"{classes}\\{prog_name}\\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)

    with winreg.CreateKey(root, f"{classes}\\{prog_name}\\Shell\\Open\\Command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{launcher}" "%1"')

    print(f"[+] {ext} files registered with custom icon and launcher.")

def register_linux_mime_type(ext, mime_type, description, icon_path):
    """Register MIME type and file association on Linux."""
    home = os.path.expanduser("~")
    
    # Create mime type definition
    mime_dir = os.path.join(home, ".local", "share", "mime", "packages")
    os.makedirs(mime_dir, exist_ok=True)
    
    mime_file = os.path.join(mime_dir, f"rachet-{ext[1:]}.xml")
    mime_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
    <mime-type type="{mime_type}">
        <comment>{description}</comment>
        <glob pattern="*{ext}"/>
    </mime-type>
</mime-info>
"""
    
    with open(mime_file, "w") as f:
        f.write(mime_content)
    
    # Update MIME database
    try:
        subprocess.run(["update-mime-database", os.path.join(home, ".local", "share", "mime")], 
                      check=False, capture_output=True)
        print(f"[+] Registered MIME type {mime_type} for {ext}")
    except FileNotFoundError:
        print("[!] update-mime-database not found, MIME type registration skipped")
    
    # Copy icon if it exists
    if os.path.exists(icon_path):
        icon_dir = os.path.join(home, ".local", "share", "icons", "hicolor", "48x48", "mimetypes")
        os.makedirs(icon_dir, exist_ok=True)
        
        icon_name = mime_type.replace("/", "-") + ".png"
        icon_dest = os.path.join(icon_dir, icon_name)
        
        # Convert ico to png if needed (requires ImageMagick)
        if icon_path.endswith(".ico"):
            try:
                subprocess.run(["convert", icon_path, icon_dest], check=False, capture_output=True)
                print(f"[+] Installed icon for {ext}")
            except FileNotFoundError:
                print("[!] ImageMagick not found, icon installation skipped")
        else:
            shutil.copy(icon_path, icon_dest)

def create_linux_desktop_entry():
    """Create .desktop file for Linux file associations."""
    home = os.path.expanduser("~")
    desktop_dir = os.path.join(home, ".local", "share", "applications")
    os.makedirs(desktop_dir, exist_ok=True)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gears_script = os.path.join(base_dir, "gears.py")
    
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Rachet Compiler
Comment=Compile Rachet source files
Exec=python3 "{gears_script}" compile %f
Icon=text-x-script
Terminal=true
Categories=Development;
MimeType=application/x-rachet;application/x-rachet-compressed;
"""
    
    desktop_file = os.path.join(desktop_dir, "rachet-compiler.desktop")
    with open(desktop_file, "w") as f:
        f.write(desktop_content)
    
    # Make it executable
    os.chmod(desktop_file, os.stat(desktop_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    print(f"[+] Created desktop entry for file associations")

def add_to_path_permanent():
    """Add current script directory to PATH permanently."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if IS_WINDOWS:
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
                refresh_current_path()
            else:
                print("[*] Directory already in PATH.")
    
    elif IS_LINUX:
        home = os.path.expanduser("~")
        shell_rc = None
        
        # Detect shell and appropriate RC file
        if os.path.exists(os.path.join(home, ".bashrc")):
            shell_rc = os.path.join(home, ".bashrc")
        elif os.path.exists(os.path.join(home, ".zshrc")):
            shell_rc = os.path.join(home, ".zshrc")
        
        if shell_rc:
            with open(shell_rc, "r") as f:
                content = f.read()
            
            path_line = f'export PATH="$PATH:{base_dir}"'
            
            if base_dir not in content:
                with open(shell_rc, "a") as f:
                    f.write(f"\n# Added by Rachet installer\n{path_line}\n")
                print(f"[+] Added {base_dir} to PATH in {shell_rc}")
                print(f"[*] Run 'source {shell_rc}' or restart your terminal to update PATH")
            else:
                print("[*] Directory already in PATH.")
        else:
            print("[!] Could not find shell RC file. Add this to your PATH manually:")
            print(f"    export PATH=\"$PATH:{base_dir}\"")

def refresh_current_path():
    """Refresh the PATH environment variable in the current session (Windows only)."""
    if not IS_WINDOWS:
        return
    
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                user_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                user_path = ""
        
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                           r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            try:
                system_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                system_path = ""
        
        combined_path = user_path + ";" + system_path if user_path and system_path else user_path or system_path
        os.environ["PATH"] = combined_path
        
        print("[+] PATH refreshed in current session.")
        
    except Exception as e:
        print(f"[!] Could not refresh PATH: {e}")

def create_gears_script():
    """Create the main gears.py script that handles compile and fetch commands."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gears_script = os.path.join(base_dir, "gears.py")
    
    gears_content = '''import os
import sys
import subprocess
import shutil
import zlib
import glob

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

def to_wsl_path(win_path: str) -> str:
    """Convert a Windows path to WSL path."""
    drive, path = os.path.splitdrive(win_path)
    return f"/mnt/{drive[0].lower()}{path.replace(chr(92), '/')}"

def to_linux_path(path: str) -> str:
    """Normalize path for Linux."""
    return os.path.abspath(path)

def compress_file(input_file, noreplace):
    """Compress a .rx or .txt file to .rxc format using zlib."""
    if not os.path.isfile(input_file):
        print(f"[!] File {input_file} not found.")
        return False

    output_file = os.path.splitext(input_file)[0] + ".rxc"

    if noreplace and os.path.exists(output_file):
        print(f"[*] {output_file} exists (use without --noreplace to overwrite)")
        return False

    try:
        with open(input_file, "rb") as f:
            data = f.read()

        compressed = zlib.compress(data, level=9)

        with open(output_file, "wb") as f:
            f.write(compressed)

        print(f"[+] Compressed {input_file} -> {output_file}")

        if not noreplace:
            os.remove(input_file)
            print(f"[+] Deleted original {input_file}")

        return True
    except Exception as e:
        print(f"[!] Error compressing {input_file}: {e}")
        return False

def uncompress_file(input_file, noreplace, to_txt=False):
    """Uncompress a .rxc file to .rx or .txt format."""
    if not os.path.isfile(input_file):
        print(f"[!] File {input_file} not found.")
        return False

    if not input_file.endswith(".rxc"):
        print(f"[!] File {input_file} is not an .rxc file")
        return False

    output_ext = ".txt" if to_txt else ".rx"
    output_file = os.path.splitext(input_file)[0] + output_ext

    if noreplace and os.path.exists(output_file):
        print(f"[*] {output_file} exists (use without --noreplace to overwrite)")
        return False

    try:
        with open(input_file, "rb") as f:
            compressed = f.read()

        data = zlib.decompress(compressed)

        with open(output_file, "wb") as f:
            f.write(data)

        print(f"[+] Uncompressed {input_file} -> {output_file}")

        if not noreplace:
            os.remove(input_file)
            print(f"[+] Deleted original {input_file}")

        return True
    except Exception as e:
        print(f"[!] Error uncompressing {input_file}: {e}")
        return False

def transform_file(input_file, noreplace):
    """Transform between .txt and .rx file extensions."""
    if not os.path.isfile(input_file):
        print(f"[!] File {input_file} not found.")
        return False

    base, ext = os.path.splitext(input_file)
    if ext == ".txt":
        output_file = base + ".rx"
    elif ext == ".rx":
        output_file = base + ".txt"
    else:
        print(f"[!] File {input_file} is neither .txt nor .rx")
        return False

    if noreplace and os.path.exists(output_file):
        print(f"[*] {output_file} exists (use without --noreplace to overwrite)")
        return False

    try:
        if os.path.exists(output_file) and not noreplace:
            os.remove(output_file)

        os.rename(input_file, output_file)
        print(f"[+] Transformed {input_file} -> {output_file}")
        return True
    except Exception as e:
        print(f"[!] Error transforming {input_file}: {e}")
        return False

def process_files(patterns, action, noreplace=False, to_txt=False):
    """Process multiple files matching the given patterns."""
    matched = 0
    for pattern in patterns:
        for file in glob.glob(pattern, recursive=True):
            if os.path.isdir(file):
                continue
            if action == "compress":
                if compress_file(file, noreplace):
                    matched += 1
            elif action == "uncompress":
                if uncompress_file(file, noreplace, to_txt=to_txt):
                    matched += 1
            elif action == "transform":
                if transform_file(file, noreplace):
                    matched += 1
    print(f"[+] Processed {matched} file(s).")
    return matched > 0

def cleanup_compiler_directory(compiler_dir):
    """Clean up temporary files in the compiler directory."""
    print("[*] Cleaning up temporary files...")
    
    temp_asm = os.path.join(compiler_dir, "temp.asm")
    if os.path.exists(temp_asm):
        os.remove(temp_asm)
        print("[+] Removed temp.asm")
    
    pycache_paths = [
        os.path.join(compiler_dir, "commands", "__pycache__"),
        os.path.join(compiler_dir, "__pycache__")
    ]
    
    for path in pycache_paths:
        try:
            shutil.rmtree(path)
            print(f"[+] Removed {os.path.basename(path)} directory")
        except (FileNotFoundError, OSError):
            pass

    iso_path = os.path.join(compiler_dir, "iso")
    try:
        shutil.rmtree(iso_path)
        print("[+] Removed iso directory")
    except (FileNotFoundError, OSError):
        pass

def move_iso_file(compiler_dir, target_dir, source_filename):
    """Move main.iso from compiler directory to target directory."""
    iso_name = "main.iso"
    
    source_iso = os.path.join(compiler_dir, iso_name)
    target_iso = os.path.join(target_dir, iso_name)
    
    if os.path.exists(source_iso):
        try:
            if os.path.exists(target_iso):
                if source_iso == target_iso:
                    return True
                else:   
                    os.remove(target_iso)
            
            shutil.move(source_iso, target_iso)
            print(f"[+] Moved main.iso to current directory")
            return True
        except Exception as e:
            print(f"[!] Could not move main.iso: {e}")
            return False
    else:
        print(f"[!] Generated ISO file main.iso not found in compiler directory")
        return False

def compile_rachet_file(file_path):
    """Compile a .rx file."""
    program_path = os.path.abspath(file_path)
    
    if not os.path.exists(program_path):
        print(f"Error: File '{file_path}' not found.")
        return 1
    
    if not program_path.endswith('.rx'):
        print(f"Error: File '{file_path}' is not a .rx file.")
        return 1
    
    program_name = os.path.basename(program_path)
    
    this_script_path = os.path.abspath(__file__)
    this_dir = os.path.dirname(this_script_path)
    compiler_dir = os.path.join(this_dir, "rachet")
    compiler_path = os.path.join(compiler_dir, "compiler.py")
    
    if not os.path.exists(compiler_path):
        print(f"Error: Compiler not found at '{compiler_path}'")
        print("Make sure the rachet/compiler.py file exists in the gears directory.")
        return 1
    
    print(f"[*] Compiling {program_name}...")
    
    if IS_WINDOWS:
        # Use WSL on Windows
        compiler_path_wsl = to_wsl_path(compiler_path)
        program_path_wsl = to_wsl_path(program_path)
        compiler_dir_wsl = to_wsl_path(compiler_dir)
        
        cmd = f"cd '{compiler_dir_wsl}' && python3 '{compiler_path_wsl}' '{program_path_wsl}'"
        
        try:
            result = subprocess.run(
                ["wsl", "bash", "-ic", cmd],
                text=True
            )
            
            if result.returncode == 0:
                print("[+] Compilation successful!")
                current_dir = os.getcwd()
                iso_moved = move_iso_file(compiler_dir, current_dir, program_name)
                cleanup_compiler_directory(compiler_dir)
                
                if iso_moved:
                    print(f"[+] Build complete! Your ISO is ready in the current directory.")
                else:
                    print("[!] Compilation completed but ISO file could not be moved.")
            
            return result.returncode
            
        except FileNotFoundError:
            print("Error: WSL not found. Make sure Windows Subsystem for Linux is installed.")
            return 1
        except Exception as e:
            print(f"Error running compiler: {e}")
            return 1
    
    elif IS_LINUX:
        # Native compilation on Linux
        try:
            result = subprocess.run(
                ["python3", compiler_path, program_path],
                cwd=compiler_dir,
                text=True
            )
            
            if result.returncode == 0:
                print("[+] Compilation successful!")
                current_dir = os.getcwd()
                iso_moved = move_iso_file(compiler_dir, current_dir, program_name)
                cleanup_compiler_directory(compiler_dir)
                
                if iso_moved:
                    print(f"[+] Build complete! Your ISO is ready in the current directory.")
                else:
                    print("[!] Compilation completed but ISO file could not be moved.")
            
            return result.returncode
            
        except Exception as e:
            print(f"Error running compiler: {e}")
            return 1
    
    else:
        print(f"Error: Unsupported platform '{sys.platform}'")
        return 1

def show_rachet_info():
    """Display Rachet ASCII art and information."""
    print("""
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
    print("  gears compile <file.rx>           Compile a Rachet source file")
    print("  gears compress <files...>         Compress .rx or .txt files to .rxc")
    print("  gears uncompress <files...>       Uncompress .rxc files to .rx")
    print("  gears transform <files...>        Toggle between .txt and .rx extensions")
    print("  gears fetch                       Show Rachet information and ASCII art")
    print("  gears help                        Show this help message")
    print("")
    print("Compression Options:")
    print("  --noreplace                       Don't overwrite existing files or delete originals")
    print("  --txt                            (uncompress only) Output as .txt instead of .rx")
    print("")
    print("Examples:")
    print("  gears compile main.rx")
    print("  gears compress *.rx")
    print("  gears compress main.rx --noreplace")
    print("  gears uncompress *.rxc")
    print("  gears uncompress main.rxc --txt")
    print("  gears transform main.txt")
    print("  gears fetch")

def parse_compression_args(args):
    """Parse compression-related arguments."""
    files = []
    noreplace = False
    to_txt = False
    
    for arg in args:
        if arg == "--noreplace":
            noreplace = True
        elif arg == "--txt":
            to_txt = True
        else:
            files.append(arg)
    
    return files, noreplace, to_txt

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
    
    elif command == "compress":
        if len(sys.argv) < 3:
            print("Error: No files specified for compression.")
            print("Usage: gears compress <files...> [--noreplace]")
            return 1
        
        files, noreplace, _ = parse_compression_args(sys.argv[2:])
        if not files:
            print("Error: No files specified for compression.")
            return 1
        
        success = process_files(files, "compress", noreplace=noreplace)
        return 0 if success else 1
    
    elif command == "uncompress":
        if len(sys.argv) < 3:
            print("Error: No files specified for uncompression.")
            print("Usage: gears uncompress <files...> [--noreplace] [--txt]")
            return 1
        
        files, noreplace, to_txt = parse_compression_args(sys.argv[2:])
        if not files:
            print("Error: No files specified for uncompression.")
            return 1
        
        success = process_files(files, "uncompress", noreplace=noreplace, to_txt=to_txt)
        return 0 if success else 1
    
    elif command == "transform":
        if len(sys.argv) < 3:
            print("Error: No files specified for transformation.")
            print("Usage: gears transform <files...> [--noreplace]")
            return 1
        
        files, noreplace, _ = parse_compression_args(sys.argv[2:])
        if not files:
            print("Error: No files specified for transformation.")
            return 1
        
        success = process_files(files, "transform", noreplace=noreplace)
        return 0 if success else 1
    
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
    """Create a launcher script for 'gears' command."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gears_script = os.path.join(base_dir, "gears.py")
    
    if IS_WINDOWS:
        bat_path = os.path.join(base_dir, "gears.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\npython "{gears_script}" %*\n')
        print(f"[+] Created launcher: {bat_path}")
    
    elif IS_LINUX:
        sh_path = os.path.join(base_dir, "gears")
        with open(sh_path, "w") as f:
            f.write(f'#!/bin/bash\npython3 "{gears_script}" "$@"\n')
        
        # Make it executable
        os.chmod(sh_path, os.stat(sh_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[+] Created launcher: {sh_path}")

def restart_explorer():
    """Restart Windows Explorer to refresh icons (Windows only)."""
    if not IS_WINDOWS:
        return
    
    print("[*] Restarting Explorer to refresh icons...")
    subprocess.run("taskkill /IM explorer.exe /F", shell=True)
    time.sleep(1)
    subprocess.run("start explorer.exe", shell=True)
    print("[+] Explorer restarted. Icons should update immediately.")

def main():
    """Main installation routine."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"[*] Installing Rachet on {sys.platform}...")
    
    if IS_WINDOWS:
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

        print("\n[*] Done! .rx and .rxc now open with compiler.exe, and 'gears' can be called from anywhere.")
        print("[*] You can now use:")
        print("    gears compile main.rx")
        print("    gears compress *.rx")
        print("    gears uncompress *.rxc")
        print("    gears fetch")
        print("    gears help")
        
        return 0
    
    elif IS_LINUX:
        print("[*] Registering MIME types...")
        register_linux_mime_type(
            ext=".rx",
            mime_type="application/x-rachet",
            description="Rachet Source File",
            icon_path=os.path.join(base_dir, "rachet.png")
        )
        
        register_linux_mime_type(
            ext=".rxc",
            mime_type="application/x-rachet-compressed",
            description="Rachet Compressed File",
            icon_path=os.path.join(base_dir, "rachet_compressed.png")
        )
        
        print("[*] Creating desktop entry...")
        create_linux_desktop_entry()
        
        add_to_path_permanent()
        create_gears_script()
        create_gears_launcher()
        
        print("\n[*] Done! File associations registered.")
        print("[*] You can now use:")
        print("    gears compile main.rx")
        print("    gears compress *.rx")
        print("    gears uncompress *.rxc")
        print("    gears fetch")
        print("    gears help")
        print("")
        print("[!] Note: You may need to restart your terminal or run:")
        home = os.path.expanduser("~")
        if os.path.exists(os.path.join(home, ".bashrc")):
            print("    source ~/.bashrc")
        elif os.path.exists(os.path.join(home, ".zshrc")):
            print("    source ~/.zshrc")
        print("    to make the 'gears' command available in your current session.")
        
        return 0
    
    else:
        print(f"[!] Unsupported platform: {sys.platform}")
        print("[*] Creating gears script anyway...")
        create_gears_script()
        create_gears_launcher()
        print("[*] You may need to manually add the directory to your PATH.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
