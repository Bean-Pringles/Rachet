import importlib.util
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser, Node
from linker import link

class Compiler:
    def __init__(self, source_file):
        self.source_file = source_file
        self.generated_text_asm = ""
        self.generated_data_asm = ""
        self.output_type = 'bin'
        self.variables = {}
        self.stack_offset = 0
        self.label_counter = 0

    def get_unique_label(self, prefix="label"):
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

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

        # Check for use statement to determine output type
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
            if node.value == 'main':
                self.generated_text_asm += "push ebp\nmov ebp, esp\n"
                # Save space for local variables at beginning of function
                old_stack_offset = self.stack_offset
                old_variables = self.variables.copy()
                self.stack_offset = 0
                self.variables = {}
                self.codegen(node.children[0])
                self.generated_text_asm += "mov esp, ebp\npop ebp\nret\n"
                self.stack_offset = old_stack_offset
                self.variables = old_variables
            else:
                # Handle function parameters
                params = node.children[1:] if len(node.children) > 1 else []
                self.generated_text_asm += "push ebp\nmov ebp, esp\n"
                
                # Save old state
                old_stack_offset = self.stack_offset
                old_variables = self.variables.copy()
                self.stack_offset = 0
                
                # Set up parameters as local variables (positive offsets from ebp)
                param_offset = 8  # Start after ebp and return address
                for param in params:
                    self.variables[param.value] = param_offset
                    param_offset += 4
                
                self.codegen(node.children[0])
                self.generated_text_asm += "mov esp, ebp\npop ebp\nret\n"
                
                # Restore old state
                self.stack_offset = old_stack_offset
                self.variables = old_variables
        elif node.type == 'Block':
            for statement in node.children:
                self.codegen(statement)
        elif node.type == 'VariableDeclaration':
            var_name = node.value
            self.stack_offset += 4
            self.variables[var_name] = -self.stack_offset  # Negative for local variables
            
            # Generate code for the expression
            self.codegen(node.children[0])
            
            # Store result in variable
            self.generated_text_asm += f"sub esp, 4\nmov [ebp{self.variables[var_name]}], eax\n"
        elif node.type == 'IfStatement':
            else_label = self.get_unique_label("else")
            end_label = self.get_unique_label("endif")
            
            # Generate condition
            self.codegen(node.children[0])
            self.generated_text_asm += f"test eax, eax\njz {else_label}\n"
            
            # Generate then block
            self.codegen(node.children[1])
            self.generated_text_asm += f"jmp {end_label}\n{else_label}:\n"
            
            # Generate else block if present
            if len(node.children) > 2:
                self.codegen(node.children[2])
            
            self.generated_text_asm += f"{end_label}:\n"
        elif node.type == 'MatchStatement':
            var_expr = node.children[0]
            end_label = self.get_unique_label("match_end")
            
            # Generate code to get the variable value (assuming it's a string pointer)
            self.codegen(var_expr)
            self.generated_text_asm += "push eax\n"  # Save the string pointer
            
            for i, case in enumerate(node.children[1:]):
                next_case_label = self.get_unique_label(f"next_case_{i}")
                
                # Create string literal for comparison
                case_str_label = self.get_unique_label("case_str")
                after_str_label = self.get_unique_label("after_case_str")
                
                self.generated_text_asm += f"jmp {after_str_label}\n"
                self.generated_text_asm += f"{case_str_label}: db '{case.value}', 0\n"
                self.generated_text_asm += f"{after_str_label}:\n"
                
                # Compare strings
                self.generated_text_asm += f"mov eax, [esp]\n"  # Get saved string pointer
                self.generated_text_asm += f"push {case_str_label}\n"
                self.generated_text_asm += f"push eax\n"
                self.generated_text_asm += f"call string_compare\n"
                self.generated_text_asm += f"add esp, 8\n"  # Clean up string_compare parameters
                self.generated_text_asm += f"test eax, eax\n"
                self.generated_text_asm += f"jz {next_case_label}\n"
                
                # Execute case action
                self.codegen(case.children[0])
                self.generated_text_asm += f"jmp {end_label}\n"
                
                self.generated_text_asm += f"{next_case_label}:\n"
            
            self.generated_text_asm += f"add esp, 4\n"  # Clean up saved pointer
            self.generated_text_asm += f"{end_label}:\n"
        elif node.type == 'BinaryOp':
            self.codegen(node.children[0])  # Left operand
            self.generated_text_asm += "push eax\n"
            self.codegen(node.children[1])  # Right operand
            self.generated_text_asm += "mov ebx, eax\npop eax\n"
            
            if node.value == 'PLUS':
                self.generated_text_asm += "add eax, ebx\n"
            elif node.value == 'MINUS':
                self.generated_text_asm += "sub eax, ebx\n"
            elif node.value == 'MULTIPLY':
                self.generated_text_asm += "imul eax, ebx\n"
            elif node.value == 'DIVIDE':
                self.generated_text_asm += "cdq\nidiv ebx\n"
            elif node.value == 'EQUAL':
                self.generated_text_asm += "cmp eax, ebx\nsete al\nmovzx eax, al\n"
            elif node.value == 'NOT_EQUAL':
                self.generated_text_asm += "cmp eax, ebx\nsetne al\nmovzx eax, al\n"
            elif node.value == 'AND':
                and_false_label = self.get_unique_label("and_false")
                and_done_label = self.get_unique_label("and_done")
                self.generated_text_asm += f"test eax, eax\njz {and_false_label}\ntest ebx, ebx\njz {and_false_label}\nmov eax, 1\njmp {and_done_label}\n{and_false_label}:\nxor eax, eax\n{and_done_label}:\n"
            elif node.value == 'OR':
                or_true_label = self.get_unique_label("or_true")
                or_done_label = self.get_unique_label("or_done")
                self.generated_text_asm += f"test eax, eax\njnz {or_true_label}\ntest ebx, ebx\njnz {or_true_label}\nxor eax, eax\njmp {or_done_label}\n{or_true_label}:\nmov eax, 1\n{or_done_label}:\n"
        elif node.type == 'UnaryOp':
            if node.value == 'NOT':
                self.codegen(node.children[0])
                self.generated_text_asm += "test eax, eax\nsetz al\nmovzx eax, al\n"
        elif node.type == 'Number':
            self.generated_text_asm += f"mov eax, {node.value}\n"
        elif node.type == 'Variable':
            if node.value in self.variables:
                offset = self.variables[node.value]
                self.generated_text_asm += f"mov eax, [ebp{offset:+d}]\n"
            else:
                raise Exception(f"Undefined variable: {node.value}")
        elif node.type == 'FunctionCall':
            command_name = node.value
            
            # Handle built-in functions
            if command_name == 'print':
                if len(node.children) > 0:
                    arg = node.children[0]
                    if arg.type == 'StringLiteral':
                        text = arg.value.strip('"')
                        # Simple handling - just replace basic escapes
                        text = text.replace('\\n', '\n')
                        # Automatically add newline if not present
                        if not text.endswith('\n'):
                            text += '\n'
                        
                        label = self.get_unique_label("str")
                        after_label = self.get_unique_label("after")
                        
                        # Convert to individual character bytes for assembly
                        char_bytes = []
                        for char in text:
                            if char == '\n':
                                char_bytes.append('10')
                            elif char == '\t':
                                char_bytes.append('9') 
                            elif char == '\r':
                                char_bytes.append('13')
                            elif char == "'":
                                char_bytes.append('39')  # ASCII for single quote
                            elif ord(char) >= 32 and ord(char) <= 126:
                                char_bytes.append(f"'{char}'")
                            else:
                                char_bytes.append(str(ord(char)))
                        
                        char_bytes.append('0')  # null terminator
                        char_string = ', '.join(char_bytes)
                        
                        self.generated_text_asm += f"jmp {after_label}\n{label}: db {char_string}\n{after_label}:\npush {label}\ncall print_thunk\n"
                            
                    elif arg.type == 'Variable':
                        if arg.value in self.variables:
                            offset = self.variables[arg.value]
                            self.generated_text_asm += f"push dword [ebp{offset:+d}]\ncall print_number_thunk\n"
            elif command_name == 'input':
                if len(node.children) > 0 and node.children[0].type == 'StringLiteral':
                    prompt = node.children[0].value.strip('"')
                    label = self.get_unique_label("prompt")
                    after_label = self.get_unique_label("after")
                    buffer_label = self.get_unique_label("input_buffer")
                    
                    # Allocate buffer in data section
                    self.generated_data_asm += f"{buffer_label}: resb 256\n"
                    
                    # Convert prompt to character bytes
                    char_bytes = []
                    for char in prompt:
                        if char == "'":
                            char_bytes.append('39')
                        elif ord(char) >= 32 and ord(char) <= 126:
                            char_bytes.append(f"'{char}'")
                        else:
                            char_bytes.append(str(ord(char)))
                    char_bytes.append('0')  # null terminator
                    char_string = ', '.join(char_bytes)
                    
                    # Generate prompt and input code
                    self.generated_text_asm += f"jmp {after_label}\n{label}: db {char_string}\n{after_label}:\n"
                    self.generated_text_asm += f"push {label}\ncall print_thunk\n"
                    self.generated_text_asm += f"push {buffer_label}\ncall input_thunk\n"
                    self.generated_text_asm += f"mov eax, {buffer_label}\n"  # Return buffer address
            elif command_name == 'os':
                if len(node.children) > 0:
                    arg = node.children[0]
                    if arg.type == 'StringLiteral' and 'shutdown' in arg.value:
                        self.generated_text_asm += "call shutdown_thunk\n"
            else:
                # Try to call user-defined function
                try:
                    # Push arguments in reverse order
                    for arg in reversed(node.children):
                        self.codegen(arg)
                        self.generated_text_asm += "push eax\n"
                    
                    # Call function
                    self.generated_text_asm += f"call {command_name}\n"
                    
                    # Clean up stack
                    if node.children:
                        self.generated_text_asm += f"add esp, {len(node.children) * 4}\n"
                except Exception as e:
                    print(f"Warning: Could not generate call for function '{command_name}': {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source_file>")
        sys.exit(1)
        
    source_file = sys.argv[1]
    compiler = Compiler(source_file)
    compiler.run()