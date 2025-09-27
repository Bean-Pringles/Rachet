import os
import sys
import subprocess

def to_wsl_path(win_path: str) -> str:
    """
    Convert a Windows path like C:\\Users\\you\\file.py
    to a WSL path like /mnt/c/Users/you/file.py
    """
    drive, path = os.path.splitdrive(win_path)
    # replace backslashes with forward slashes
    return f"/mnt/{drive[0].lower()}{path.replace('\\', '/')}"

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
    print(f"[*] Working directory: {program_dir}")
    
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

def show_help():
    """Show help information."""
    print("Gears - Rachet Language Toolchain")
    print("")
    print("Usage:")
    print("  gears compile <file.rx>    Compile a Rachet source file")
    print("  gears help                 Show this help message")
    print("")
    print("Examples:")
    print("  gears compile main.rx")
    print("  gears compile src/hello.rx")

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
    
    elif command == "help" or command == "--help" or command == "-h":
        show_help()
        return 0
    
    else:
        print(f"Error: Unknown command '{command}'")
        show_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
