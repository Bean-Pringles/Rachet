import subprocess
import os

def link(generated_data, generated_text, output_type):
    NASM_COMMAND = "nasm"
    LD_COMMAND = "ld"
    GRUB_COMMAND = "grub-mkrescue"

    # Read the kernel from the separate file
    kernel_file = 'runtimes/kernel.asm'
    if not os.path.exists(kernel_file):
        raise FileNotFoundError(f"Kernel file '{kernel_file}' not found. Please ensure kernel.asm exists.")
    
    with open(kernel_file, 'r') as f:
        kernel_asm = f.read()
    
    # Combine kernel with generated code
    final_asm = f"{kernel_asm}\n\nsection .data\n{generated_data}\n\nsection .text\n{generated_text}"
    
    with open('temp.asm', 'w') as f:
        f.write(final_asm)
    
    try:
        subprocess.run([NASM_COMMAND, 'temp.asm', '-f', 'elf32', '-o', 'temp.o'], check=True)
        subprocess.run([LD_COMMAND, '-m', 'elf_i386', '-Ttext', '0x100000', 'temp.o', '-o', 'kernel.elf'], check=True)

        if output_type == 'iso':
            os.makedirs('iso/boot/grub', exist_ok=True)
            with open('iso/boot/grub/grub.cfg', 'w') as f:
                f.write("set timeout=0\n")
                f.write("set default=0\n") 
                f.write("menuentry \"myLang OS\" {\n")
                f.write("  multiboot /boot/kernel.elf\n")
                f.write("}\n")
            
            os.rename('kernel.elf', 'iso/boot/kernel.elf')
            subprocess.run([GRUB_COMMAND, '--output=main.iso', 'iso'], check=True)
            print("Successfully created main.iso")
        
        elif output_type == 'bin':
            os.rename('kernel.elf', 'main.bin')
            print("Successfully created main.bin")

        # Clean up temporary files
        if os.path.exists('temp.asm'):
            os.remove('temp.asm')
        if os.path.exists('temp.o'):
            os.remove('temp.o')
            
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    print("This module provides the link() function for the compiler.")
    print("Usage: from linker import link")