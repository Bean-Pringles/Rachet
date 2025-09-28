import os
import sys
import subprocess
import shutil
import zlib
import glob

def to_wsl_path(win_path: str) -> str:
    """
    Convert a Windows path like C:\\Users\\you\\file.py
    to a WSL path like /mnt/c/Users/you/file.py
    """
    drive, path = os.path.splitdrive(win_path)
    # replace backslashes with forward slashes
    return f"/mnt/{drive[0].lower()}{path.replace('\\', '/')}"

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
    
    # Remove temp.asm if it exists
    temp_asm = os.path.join(compiler_dir, "temp.asm")
    if os.path.exists(temp_asm):
        os.remove(temp_asm)
        print("[+] Removed temp.asm")
    
    # Remove __pycache__ directories
    pycache_paths = [
        os.path.join(compiler_dir, "commands", "__pycache__"),
        os.path.join(compiler_dir, "__pycache__")
    ]
    
    for path in pycache_paths:
        try:
            shutil.rmtree(path)
            print(f"[+] Removed {os.path.basename(path)} directory")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[!] Could not remove {path}: {e}")

    # Remove iso folder
    iso_path = os.path.join(compiler_dir, "iso")
    try:
        shutil.rmtree(iso_path)
        print("[+] Removed iso directory")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[!] Could not remove iso directory: {e}")

def move_iso_file(compiler_dir, target_dir, source_filename):
    """Move main.iso from compiler directory to target directory."""
    iso_name = "main.iso"
    
    source_iso = os.path.join(compiler_dir, iso_name)
    target_iso = os.path.join(target_dir, iso_name)
    
    if os.path.exists(source_iso):
        try:
            # If target file already exists, remove it first
            if os.path.exists(target_iso):
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
    
    # Directory of the target program (where gears was called from)
    program_dir = os.path.dirname(program_path)
    program_name = os.path.basename(program_path)
    
    # Find compiler.py (assumes it lives in rachet/ under this script's directory)
    this_script_path = os.path.abspath(__file__)
    this_dir = os.path.dirname(this_script_path)
    compiler_dir = os.path.join(this_dir, "rachet")
    compiler_path = os.path.join(compiler_dir, "compiler.py")
    
    # Check if compiler exists
    if not os.path.exists(compiler_path):
        print(f"Error: Compiler not found at '{compiler_path}'")
        print("Make sure the rachet/compiler.py file exists in the gears directory.")
        return 1
    
    # Convert paths to WSL format
    compiler_path_wsl = to_wsl_path(compiler_path)
    program_path_wsl = to_wsl_path(program_path)
    compiler_dir_wsl = to_wsl_path(compiler_dir)
    
    print(f"[*] Compiling {program_name}...")
    
    # Run inside WSL in the compiler directory, but pass the full path to the source file
    # Using bash -ic so PATH and tools like xorriso work
    cmd = f"cd '{compiler_dir_wsl}' && python3 '{compiler_path_wsl}' '{program_path_wsl}'"
    
    try:
        # Run the compiler with real-time output
        result = subprocess.run(
            ["wsl", "bash", "-ic", cmd],
            text=True
        )
        
        if result.returncode == 0:
            # Compilation successful, now move the ISO and cleanup
            print("[+] Compilation successful!")
            
            # Move the generated ISO file to the directory where gears was called
            current_dir = os.getcwd()
            iso_moved = move_iso_file(compiler_dir, current_dir, program_name)
            
            # Clean up temporary files in compiler directory
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
    print("")
    print("Note: The generated ISO file will be moved to the current directory")
    print("      and temporary files will be cleaned up automatically.")


def parse_compression_args(args):
    """Parse compression-related arguments and return (files, noreplace, to_txt)."""
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
