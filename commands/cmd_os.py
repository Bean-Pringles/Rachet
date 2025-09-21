# commands/cmd_os.py

def compile(args):
    command = args[0].value
    
    if command == "shutdown":
        return {
            "data": "",
            "text": "call shutdown_thunk"
        }
    else:
        return {
            "data": "",
            "text": "; os command not recognized"
        }