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

# -----------------------------------------------------------
# Ensure the user gave us a program to compile
# -----------------------------------------------------------
if len(sys.argv) < 2:
    print("Usage: python run_compiler.py <path-to-program>")
    sys.exit(1)

# Path to the target program
programFile = sys.argv[1]

# Resolve to absolute path
programPath = os.path.abspath(programFile)

# Directory of the target program
programDir = os.path.dirname(programPath)

# -----------------------------------------------------------
# Find compiler.py (assumes it lives in rachet/ under this script)
# -----------------------------------------------------------
thisScriptPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisScriptPath)
compilerPath = os.path.join(thisDir, "rachet", "compiler.py")

# -----------------------------------------------------------
# Convert paths to WSL format
# -----------------------------------------------------------
compilerPath_wsl = to_wsl_path(compilerPath)
programDir_wsl = to_wsl_path(programDir)
programName = os.path.basename(programPath)

# -----------------------------------------------------------
# Run inside WSL in the program’s directory
# Using bash -ic so PATH and tools like xorriso work
# -----------------------------------------------------------
cmd = f"cd '{programDir_wsl}' && python3 '{compilerPath_wsl}' '{programName}'"

result = subprocess.run(
    ["wsl", "bash", "-ic", cmd],
    capture_output=True,
    text=True
)

# -----------------------------------------------------------
# Output from the compiler
# -----------------------------------------------------------
print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr, file=sys.stderr)