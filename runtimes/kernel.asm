[bits 32]

; Multiboot header
align 4
multiboot_header:
dd 0x1BADB002           ; magic
dd 0x00000000           ; flags
dd -(0x1BADB002)        ; checksum

global _start
_start:
    ; Set up stack
    mov esp, 0x90000
    
    ; Completely clear VGA buffer
    mov edi, 0xB8000
    mov ecx, 4000           ; 80*25*2 = 4000 bytes (chars + attributes)
    xor eax, eax            ; Clear with zeros
    rep stosb
    
    ; Reset cursor to top-left
    mov dword [cursor_pos], 0
    
    ; Call the main function (your compiled code)
    call main
    
    ; If main returns, halt
    cli
.hang:
    hlt
    jmp .hang

global print_thunk
print_thunk:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push eax
    
    ; Get string pointer from stack
    mov esi, [ebp+8]
    
    ; Get current cursor position
    mov edi, 0xB8000
    add edi, [cursor_pos]
    
    ; Print each character
.loop:
    mov al, [esi]       ; Load character
    test al, al         ; Check for null
    jz .done
    
    cmp al, 10          ; Check for newline
    je .newline
    
    mov ah, 0x0F        ; White on black
    mov [edi], ax       ; Store char + attribute  
    add edi, 2          ; Next position
    inc esi             ; Next character
    jmp .loop

.newline:
    ; Move to start of next line
    mov eax, edi
    sub eax, 0xB8000    ; Get current offset
    add eax, 160        ; Add full line width
    mov ebx, 160
    xor edx, edx
    div ebx             ; Get line number
    mul ebx             ; Start of next line
    mov edi, eax
    add edi, 0xB8000
    inc esi
    jmp .loop
    
.done:
    ; Update cursor position
    sub edi, 0xB8000
    mov [cursor_pos], edi
    
    pop eax
    pop edi  
    pop esi
    pop ebp
    ret 4

global shutdown_thunk
shutdown_thunk:
    cli
.hang:
    hlt
    jmp .hang

cursor_pos dd 0