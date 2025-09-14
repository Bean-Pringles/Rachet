import os
import shutil

def tempAsmFile():
    if os.path.exists("temp.asm"):
        os.remove("temp.asm")
        return 1
    return 0
    
def isoPycache():
    if os.path.exists("main.iso"):
        os.remove("main.iso")
    
    if os.path.exists("iso"):
        shutil.rmtree("iso")
    
    if os.path.exists("__pycache__"):
        shutil.rmtree("__pycache__")

tempAsmFile()
isoPycache()
