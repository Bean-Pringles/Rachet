import importlib.util
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from linker import link

class Compiler:
    def __init__(self, source_file):
        self.source_file = source_file
        self.generated_text_asm = ""
        self.generated_data_asm = ""
        self.output_type = 'bin'

    def run(self):
        try:
            with open(self.source_file, 'r') as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"Error: Source file '{self.source_file}' not found.")
            return

        print("1. Lexing source code...")
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        print("2. Parsing tokens into AST...")
        parser = Parser(tokens)
        ast = parser.parse()

        for child in ast.children:
            if child.type == 'UseStatement':
                self.output_type = child.value
                break
        
        print("3. Generating assembly code from AST...")
        self.codegen(ast)
        
        print(f"4. Linking and creating main.{self.output_type}...")
        link(self.generated_data_asm, self.generated_text_asm, self.output_type)

    def codegen(self, node):
        if node.type == 'Program':
            for child in node.children:
                self.codegen(child)
        elif node.type == 'FunctionDeclaration':
            self.generated_text_asm += f"global {node.value}\n{node.value}:\n"
            self.codegen(node.children[0])
        elif node.type == 'Block':
            for statement in node.children:
                self.codegen(statement)
        elif node.type == 'FunctionCall':
            command_name = node.value
            args = node.children[0].children
            
            module_path = f"commands.cmd_{command_name}"
            spec = importlib.util.spec_from_file_location(module_path, f"commands/cmd_{command_name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            output = module.compile(args)
            if isinstance(output, dict):
                self.generated_text_asm += output.get("text", "") + "\n"
                self.generated_data_asm += output.get("data", "") + "\n"
            else:
                self.generated_text_asm += output + "\n"

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source_file>")
        sys.exit(1)
        
    source_file = sys.argv[1]
    compiler = Compiler(source_file)
    compiler.run()