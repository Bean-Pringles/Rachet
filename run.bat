@echo off
REM Rachet Language Runner for Windows - Updated for new structure

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.6 or later
    exit /b 1
)

REM Check if source file is provided
if "%1"=="" (
    echo Usage: run.bat ^<source_file.rachet^>
    echo.
    echo Example: run.bat example.rachet
    exit /b 1
)

REM Check if source file exists
if not exist "%1" (
    echo Error: Source file '%1' not found
    exit /b 1
)

REM Check if frontend.py exists
if not exist "frontend.py" (
    echo Error: frontend.py not found
    echo Make sure you're running this script from the rachetFinished directory
    exit /b 1
)

REM Check if compiler.exe exists
if not exist "compiler\compiler.exe" (
    echo Error: compiler\compiler.exe not found
    echo Please run build.bat from the root directory to build the compiler
    exit /b 1
)

REM Check if commands directory exists
if not exist "compiler\commands" (
    echo Error: compiler\commands directory not found
    echo Please run build.bat from the root directory to build the commands
    exit /b 1
)

REM Check for at least one command executable
set "found_commands="
for %%f in (compiler\commands\*.exe) do (
    set "found_commands=1"
    goto :commands_found
)

if not defined found_commands (
    echo Warning: No command executables found in compiler\commands\
    echo Please run build.bat from the root directory to build the commands
    echo The program may not work as expected
)

:commands_found

echo Running Rachet program: %1
echo.

REM Run the frontend and pipe to compiler
python frontend.py "%1" | compiler\compiler.exe

if errorlevel 1 (
    echo.
    echo Execution failed with error code %errorlevel%
    exit /b %errorlevel%
)

echo.
echo Program completed successfully