def compile(args):
    text = args[0].value.strip('"')
    
    import uuid
    label = f"str_{uuid.uuid4().hex[:8]}"
    after_label = f"after_{uuid.uuid4().hex[:8]}"

    return {
        "data": "",
        "text": f"jmp {after_label}\n{label}: db '{text}', 0\n{after_label}:\npush {label}\ncall print_thunk"
    }