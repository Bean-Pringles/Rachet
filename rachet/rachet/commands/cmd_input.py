# commands/cmd_input.py

# Global flag to track if input_buffer has been defined
_input_buffer_defined = False

def compile(args):
    global _input_buffer_defined
    
    # Only define the buffer once
    bss_section = ""
    if not _input_buffer_defined:
        bss_section = "input_buffer resb 256\n"
        _input_buffer_defined = True
    
    if not args:
        # No prompt, just get input
        return {
            "data": "",
            "text": "push input_buffer\ncall input_thunk\nmov eax, input_buffer\n",
            "bss": bss_section
        }
    
    arg = args[0]
    
    # First print the prompt, then get input
    if arg.type == 'StringLiteral':
        return {
            "data": "",
            "text": "push eax\ncall print_thunk\npush input_buffer\ncall input_thunk\nmov eax, input_buffer\n",
            "bss": bss_section
        }
    else:
        return {
            "data": "",
            "text": "push eax\ncall print_thunk\npush input_buffer\ncall input_thunk\nmov eax, input_buffer\n",
            "bss": bss_section
        }