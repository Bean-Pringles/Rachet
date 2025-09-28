# commands/cmd_print.py

def compile(args):
    import uuid
    
    if not args:
        return {
            "data": "",
            "text": "; print with no arguments\n"
        }
    
    arg = args[0]
    newline_label = f"newline_{uuid.uuid4().hex[:8]}"
    
    if arg.type == "StringLiteral":
        text = arg.value.strip('"').replace('\\n', '\n')
        label = f"str_{uuid.uuid4().hex[:8]}"
        
        return {
            "data": f'{label}: db "{text}",0\n{newline_label}: db 0x0A,0\n',
            "text": f"    push {label}\n    call print_thunk\n    push {newline_label}\n    call print_thunk\n"
        }
    elif arg.type == "Variable":
        # Use the heuristic approach since we can't easily access compiler type info here
        uuid_hex = uuid.uuid4().hex[:8]
        return {
            "data": f"{newline_label}: db 0x0A,0\n",
            "text": f"""    mov eax, dword {arg.asm}
    ; Heuristic: if value < 1000000, treat as number; otherwise as string pointer
    cmp eax, 1000000
    jl .print_as_number_{uuid_hex}
    ; Treat as string pointer
    push eax
    call print_thunk
    jmp .done_{uuid_hex}
.print_as_number_{uuid_hex}:
    push eax
    call print_number_thunk
.done_{uuid_hex}:
    push {newline_label}
    call print_thunk
"""
        }
    elif arg.type == "Number":
        return {
            "data": f"{newline_label}: db 0x0A,0\n",
            "text": f"    push dword {arg.value}\n    call print_number_thunk\n    push {newline_label}\n    call print_thunk\n"
        }
    else:
        # For other expressions, assume result is in eax
        return {
            "data": f"{newline_label}: db 0x0A,0\n",
            "text": f"    push eax\n    call print_number_thunk\n    push {newline_label}\n    call print_thunk\n"
        }