#!/bin/bash
# Rachet Language Runner for Unix/Linux/macOS - Updated for new structure

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}Error: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}Warning: $1${NC}"
}

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "Python is not installed or not in PATH"
    echo "Please install Python 3.6 or later"
    exit 1
fi

# Prefer python3 if available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Check if source file is provided
if [ $# -eq 0 ]; then
    print_error "No source file provided"
    echo "Usage: ./run.sh <source_file.rachet>"
    echo ""
    echo "Example: ./run.sh example.rachet"
    exit 1
fi

SOURCE_FILE="$1"

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    print_error "Source file '$SOURCE_FILE' not found"
    exit 1
fi

# Check if frontend.py exists
if [ ! -f "frontend.py" ]; then
    print_error "frontend.py not found"
    echo "Make sure you're running this script from the rachetFinished directory"
    exit 1
fi

# Check if compiler executable exists
COMPILER_PATH=""
if [ -f "compiler/compiler" ]; then
    COMPILER_PATH="compiler/compiler"
elif [ -f "compiler/compiler.exe" ]; then
    COMPILER_PATH="compiler/compiler.exe"
else
    print_error "Compiler executable not found"
    echo "Please run the build script from the root directory to build the compiler"
    echo "Expected: compiler/compiler (Unix) or compiler/compiler.exe (Windows)"
    exit 1
fi

# Check if compiler is executable
if [ ! -x "$COMPILER_PATH" ]; then
    print_error "Compiler '$COMPILER_PATH' is not executable"
    echo "Please make the compiler executable: chmod +x $COMPILER_PATH"
    exit 1
fi

# Check if commands directory exists
if [ ! -d "compiler/commands" ]; then
    print_error "compiler/commands directory not found"
    echo "Please run the build script from the root directory to build the commands"
    exit 1
fi

# Check for command executables
COMMANDS_FOUND=0
for cmd_file in compiler/commands/*; do
    if [ -f "$cmd_file" ] && [ -x "$cmd_file" ]; then
        COMMANDS_FOUND=1
        break
    fi
done

if [ $COMMANDS_FOUND -eq 0 ]; then
    print_warning "No executable commands found in compiler/commands/"
    echo "Please run the build script from the root directory to build the commands"
    echo "The program may not work as expected"
fi

echo "Running Rachet program: $SOURCE_FILE"
echo ""

# Run the frontend and pipe to compiler
if ! $PYTHON_CMD frontend.py "$SOURCE_FILE" | "$COMPILER_PATH"; then
    echo ""
    print_error "Execution failed"
    exit 1
fi

echo ""
print_success "Program completed successfully"