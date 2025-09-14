# Dependencies:

1. WSL (If on windows)

2. NASM

3. Grub 

4. Xorriso

5. Python

# To run:

1. First run wsl, this will boot you into wsl.

2. Navigate to the directory this is in.

3. Run python3 reset.py to get rid of any iso, pycache, temp assembley, or iso folder.

4. Run python3 compiler.py <Your codes name (Mine is main.src I would put main.src)>

5. Boot the new ISO using qemu with the command: 
qemu-system-i386 -cdrom main.iso -boot d -no-reboot

6. When you are done and want to retest run python3 reset.py

# Syntax:

Right now this is just a Hello, World! language.
Syntax is shown below (it can also be found in main.src):

use crate::iso;

fn main() {
    print("Hello World!");
    os("shutdown");
}

The use crate::iso line tells the compiler to make it into an iso file.

The fn main is the function that is first ran.

print("Hello World!") prints Hello World to the screen throught the VGA Buffer.

os("Shutdown") stops the kernal.

# To come:

1. Add a input function

2. Add varibles and strings

3. Add if statements

4. Add unsafe blocks

5. Lots of tears.
