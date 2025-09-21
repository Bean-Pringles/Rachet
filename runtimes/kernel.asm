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

global print_number_thunk
print_number_thunk:
    push ebp
    mov ebp, esp
    push eax
    push ebx
    push ecx
    push edx
    
    mov eax, [ebp+8]    ; Get number to print
    mov ebx, 10         ; Divisor
    mov ecx, 0          ; Digit counter
    
    ; Handle negative numbers
    test eax, eax
    jns .positive
    neg eax
    push eax
    mov al, '-'
    mov ah, 0x0F
    mov edi, 0xB8000
    add edi, [cursor_pos]
    mov [edi], ax
    add dword [cursor_pos], 2
    pop eax
    
.positive:
    ; Convert number to string (in reverse)
.convert:
    xor edx, edx
    div ebx
    add edx, '0'
    push edx
    inc ecx
    test eax, eax
    jnz .convert
    
    ; Print digits
    mov edi, 0xB8000
    add edi, [cursor_pos]
    
.print_digits:
    pop eax
    mov ah, 0x0F
    mov [edi], ax
    add edi, 2
    dec ecx
    jnz .print_digits
    
    ; Update cursor position
    sub edi, 0xB8000
    mov [cursor_pos], edi
    
    pop edx
    pop ecx
    pop ebx
    pop eax
    pop ebp
    ret 4

global input_thunk
input_thunk:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push eax
    push ebx
    
    mov edi, [ebp+8]    ; Buffer pointer
    xor esi, esi        ; Character count
    
.input_loop:
    ; Wait for keypress using polling
    call get_keystroke
    test al, al
    jz .input_loop      ; No key pressed, keep waiting
    
    ; Check for Enter key
    cmp al, 13
    je .input_done
    
    ; Check for Backspace
    cmp al, 8
    je .backspace
    
    ; Ignore non-printable characters
    cmp al, 32
    jb .input_loop
    cmp al, 126
    ja .input_loop
    
    ; Store character in buffer
    mov [edi + esi], al
    inc esi
    
    ; Echo character to screen
    mov ah, 0x0F
    mov ebx, 0xB8000
    add ebx, [cursor_pos]
    mov [ebx], ax
    add dword [cursor_pos], 2
    
    jmp .input_loop

.backspace:
    ; Don't backspace if at beginning
    test esi, esi
    jz .input_loop
    
    ; Remove character from buffer
    dec esi
    mov byte [edi + esi], 0
    
    ; Move cursor back and clear character
    sub dword [cursor_pos], 2
    mov ebx, 0xB8000
    add ebx, [cursor_pos]
    mov word [ebx], 0x0F20  ; Space with white attribute
    
    jmp .input_loop

.input_done:
    ; Null-terminate string
    mov byte [edi + esi], 0
    
    ; Print newline
    mov al, 10
    mov ah, 0x0F
    mov ebx, 0xB8000
    add ebx, [cursor_pos]
    mov [ebx], ax
    
    ; Move to next line
    mov eax, [cursor_pos]
    add eax, 160
    mov ebx, 160
    xor edx, edx
    div ebx
    mul ebx
    mov [cursor_pos], eax
    
    pop ebx
    pop eax
    pop edi
    pop esi
    pop ebp
    ret 4

; Simple keyboard input function
get_keystroke:
    push ebx
    push ecx
    push edx
    
    ; Check if key is available in keyboard controller
    in al, 0x64
    test al, 1
    jz .no_key
    
    ; Read the key
    in al, 0x60
    
    ; Convert scan code to ASCII (simplified)
    call scancode_to_ascii
    jmp .done
    
.no_key:
    xor al, al
    
.done:
    pop edx
    pop ecx
    pop ebx
    ret

; Simplified scan code to ASCII conversion
scancode_to_ascii:
    ; Basic scan code to ASCII table
    cmp al, 0x1E
    je .key_a
    cmp al, 0x30
    je .key_b
    cmp al, 0x2E
    je .key_c
    cmp al, 0x20
    je .key_d
    cmp al, 0x12
    je .key_e
    cmp al, 0x21
    je .key_f
    cmp al, 0x22
    je .key_g
    cmp al, 0x23
    je .key_h
    cmp al, 0x17
    je .key_i
    cmp al, 0x24
    je .key_j
    cmp al, 0x25
    je .key_k
    cmp al, 0x26
    je .key_l
    cmp al, 0x32
    je .key_m
    cmp al, 0x31
    je .key_n
    cmp al, 0x18
    je .key_o
    cmp al, 0x19
    je .key_p
    cmp al, 0x10
    je .key_q
    cmp al, 0x13
    je .key_r
    cmp al, 0x1F
    je .key_s
    cmp al, 0x14
    je .key_t
    cmp al, 0x16
    je .key_u
    cmp al, 0x2F
    je .key_v
    cmp al, 0x11
    je .key_w
    cmp al, 0x2D
    je .key_x
    cmp al, 0x15
    je .key_y
    cmp al, 0x2C
    je .key_z
    cmp al, 0x1C
    je .key_enter
    cmp al, 0x0E
    je .key_backspace
    cmp al, 0x39
    je .key_space
    
    ; Number keys
    cmp al, 0x02
    je .key_1
    cmp al, 0x03
    je .key_2
    cmp al, 0x04
    je .key_3
    cmp al, 0x05
    je .key_4
    cmp al, 0x06
    je .key_5
    cmp al, 0x07
    je .key_6
    cmp al, 0x08
    je .key_7
    cmp al, 0x09
    je .key_8
    cmp al, 0x0A
    je .key_9
    cmp al, 0x0B
    je .key_0
    
    ; Unknown key
    xor al, al
    ret

.key_a: mov al, 'a'; ret
.key_b: mov al, 'b'; ret
.key_c: mov al, 'c'; ret
.key_d: mov al, 'd'; ret
.key_e: mov al, 'e'; ret
.key_f: mov al, 'f'; ret
.key_g: mov al, 'g'; ret
.key_h: mov al, 'h'; ret
.key_i: mov al, 'i'; ret
.key_j: mov al, 'j'; ret
.key_k: mov al, 'k'; ret
.key_l: mov al, 'l'; ret
.key_m: mov al, 'm'; ret
.key_n: mov al, 'n'; ret
.key_o: mov al, 'o'; ret
.key_p: mov al, 'p'; ret
.key_q: mov al, 'q'; ret
.key_r: mov al, 'r'; ret
.key_s: mov al, 's'; ret
.key_t: mov al, 't'; ret
.key_u: mov al, 'u'; ret
.key_v: mov al, 'v'; ret
.key_w: mov al, 'w'; ret
.key_x: mov al, 'x'; ret
.key_y: mov al, 'y'; ret
.key_z: mov al, 'z'; ret
.key_enter: mov al, 13; ret
.key_backspace: mov al, 8; ret
.key_space: mov al, ' '; ret
.key_1: mov al, '1'; ret
.key_2: mov al, '2'; ret
.key_3: mov al, '3'; ret
.key_4: mov al, '4'; ret
.key_5: mov al, '5'; ret
.key_6: mov al, '6'; ret
.key_7: mov al, '7'; ret
.key_8: mov al, '8'; ret
.key_9: mov al, '9'; ret
.key_0: mov al, '0'; ret

global string_compare
string_compare:
    push ebp
    mov ebp, esp
    push esi
    push edi
    
    mov esi, [ebp+8]    ; First string
    mov edi, [ebp+12]   ; Second string
    
.compare_loop:
    mov al, [esi]
    mov bl, [edi]
    
    ; Check if both reached end
    test al, al
    jz .check_end
    test bl, bl
    jz .not_equal
    
    ; Compare characters
    cmp al, bl
    jne .not_equal
    
    ; Move to next character
    inc esi
    inc edi
    jmp .compare_loop

.check_end:
    ; Check if second string also ended
    test bl, bl
    jz .equal
    
.not_equal:
    xor eax, eax        ; Return 0 (not equal)
    jmp .done
    
.equal:
    mov eax, 1          ; Return 1 (equal)
    
.done:
    pop edi
    pop esi
    pop ebp
    ret 8

global shutdown_thunk
shutdown_thunk:
    ; Try ACPI shutdown first
    mov ax, 0x2000
    mov dx, 0x604
    out dx, ax
    
    ; If ACPI fails, try APM
    mov ax, 0x5307
    mov bx, 0x0001
    mov cx, 0x0003
    int 0x15
    
    ; If all else fails, halt
    cli
.hang:
    hlt
    jmp .hang

; Data section
cursor_pos dd 0