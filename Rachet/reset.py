import os
import shutil

def tempAsmFile():
    if os.path.exists("temp.asm"):
        os.remove("temp.asm")
        return 1
    return 0
    
def isoPycache():
    # Remove main.iso
    if os.path.exists("main.iso"):
        os.remove("main.iso")

    # Remove __pycache__ directories
    for path in ["commands/__pycache__", "__pycache__"]:
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass

    # Remove iso folder
    try:
        shutil.rmtree("iso")
    except FileNotFoundError:
        pass

if __name__ == "__main__":
    tempAsmFile()
    isoPycache()