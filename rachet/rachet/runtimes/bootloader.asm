[org 0x7c00]
bits 16
mov ax, 0x07c0
mov ds, ax
mov es, ax

; The bootloader's job is to load the kernel, but since grub-mkrescue
; handles this, we can make our bootloader minimal and let GRUB call the kernel.
; The entry point will now be the multiboot header's start address.
; Our kernel stub is now a 32-bit program.

; Your kernel stub is what GRUB will now jump to, so your original
; `jmp start_kernel` and the `kernel.asm` file are obsolete with the Multiboot protocol.
; You must combine the functionality into a single kernel file.