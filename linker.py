import subprocess
import os

def link(generated_data, generated_text, output_type):
    NASM_COMMAND = "nasm"
    LD_COMMAND = "ld"
    GRUB_COMMAND = "grub-mkrescue"

    with open('runtimes/kernel.asm', 'r') as f:
        kernel_asm = f.read()

    final_asm = f"{kernel_asm}\n\nsection .data\n{generated_data}\n\nsection .text\n{generated_text}"
    
    with open('temp.asm', 'w') as f:
        f.write(final_asm)
    
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

    os.remove('temp.asm')
    os.remove('temp.o')