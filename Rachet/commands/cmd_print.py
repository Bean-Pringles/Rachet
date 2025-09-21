def compile(args):
    text = args[0].value.strip('"').replace('\\n', '\n')

    import uuid
    label = f"str_{uuid.uuid4().hex[:8]}"
    after_label = f"after_{uuid.uuid4().hex[:8]}"

    if args[0].type == "StringLiteral":
        return {
            "data": f'{label}: db "{text}",0\n',
            "text": f"    push {label}\n    call print_thunk\n"
        }
    else:
        return {
            "data": "str_newline: db 0x0A,0\n",  # <--- ADD THIS
            "text": (
                f"    push {args[0].asm}\n"
                f"    call print_number_thunk\n"
                f"    push str_newline\n"         # <--- APPEND \n
                f"    call print_thunk\n"
            )
        }
