# commands/cmd_pause.py

def compile(args):
    if not args:
        # Default pause of 1000ms
        return {
            "data": "",
            "text": "push 1000\ncall pause_thunk\n",
            "bss": ""
        }
    
    arg = args[0]
    
    if arg.type == 'Number':
        return {
            "data": "",
            "text": f"push {arg.value}\ncall pause_thunk\n",
            "bss": ""
        }
    elif arg.type == 'Variable':
        return {
            "data": "",
            "text": f"mov eax, dword {arg.asm}\npush eax\ncall pause_thunk\n",
            "bss": ""
        }
    else:
        # For expressions, the result should already be in eax
        return {
            "data": "",
            "text": "push eax\ncall pause_thunk\n",
            "bss": ""
        }