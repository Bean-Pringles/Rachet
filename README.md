## License

This compiler is licensed under the [Bean Pringles Compiler License (BPC License) v1.0]
(https://github.com/Bean-Pringles/Rachet/blob/main/LICENSE.md).

# Dependencies:

1. WSL (If on windows)

2. NASM

3. Grub 

4. Xorriso

5. Python

6. Pyinstaller

# VS Code Extension

To get the official Rachet extension you can either:

a) Search for the rachet extenion in VS Code by Bean Pringles

b) Press ctrl + shift + p in VS Code and find Developer: Install Extension From Location.
   Then click on the VSExtension folder and click continue.
   (Please be aware this is for a one time install)

c) Press ctrl + shift + p in VS Code and find Developer: Install Extension From Location.
   Then click on the VSExtension folder and choose the vsix file.

# Set Up

1. Naviagate to the home directory with setup.py

2. Run pyinstaller --onefile --noconsole compiler.py

3. Move the compiled exe back to the folder the setup.py is located in

4. Run python setup.py (This gives the files its own icon, and it also adds gears to path)

# To run:
***Make sure it isn't a compressed file, .rxc***

1. First run wsl, this will boot you into wsl.

2. Navigate to the directory this is in.

3. Run python3 reset.py to get rid of any iso, pycache, temp assembley, or iso folder.

4. Run python3 compiler.py <Your code's name (Mine is main.rcht, so I would put main.rcht)>

5. Boot the new ISO using qemu with the command: 
qemu-system-i386 -cdrom main.iso -boot d -no-reboot

6. When you are done and want to retest run python3 reset.py

# Syntax:

Right now this is just a Hello, World! language.
Syntax is shown below (it can also be found in main.src):

use crate::iso;

fn main() {
    print("Hello World!");
    let x = 5;
    print(x);
}

The use crate::iso line tells the compiler to make it into an iso file.

The fn main is the function that is first ran.

print("Hello World!") prints Hello World to the screen throught the VGA Buffer.

The let x = 5 command assigns the varible x to the value of 5.

print(x) prints the value of x, you can tell because it doesn't have quotes.

# To come:

1. Add a input function

2. Add unsafe blocks

3. Lots of tears

4. Lots of tears.
