import importlib.util
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser, Node
from linker import link

class Compiler:
    def __init__(self, source_file):
        # Check if file has .rx extension
        if not source_file.endswith('.rx'):
            raise Exception(f"Error: Only .rx files are supported. '{source_file}' is not a valid source file.")
        
        self.source_file = source_file
        self.generated_text_asm = ""
        self.generated_data_asm = ""
        self.generated_bss_asm = ""
        self.output_type = 'bin'
        self.variables = {}
        self.stack_offset = 0
        self.label_counter = 0
        self.commands_cache = {}

    def get_unique_label(self, prefix="label"):
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def load_command(self, command_name):
        """Load command from commands subfolder"""
        if command_name in self.commands_cache:
            return self.commands_cache[command_name]
            
        commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
        command_file = os.path.join(commands_dir, f'cmd_{command_name}.py')
        
        if not os.path.exists(command_file):
            return None
            
        try:
            spec = importlib.util.spec_from_file_location(f"cmd_{command_name}", command_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.commands_cache[command_name] = module
            return module
        except Exception as e:
            print(f"Warning: Could not load command '{command_name}': {e}")
            return None

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
        link(self.generated_data_asm, self.generated_text_asm, self.output_type, self.generated_bss_asm)

    def codegen(self, node):
        if node.type == 'Program':
            for child in node.children:
                self.codegen(child)
        elif node.type == 'FunctionDeclaration':
            self.generated_text_asm += f"global {node.value}\n{node.value}:\n"
            if node.value == 'main':
                self.generated_text_asm += "push ebp\nmov ebp, esp\n"
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
                
                old_stack_offset = self.stack_offset
                old_variables = self.variables.copy()
                self.stack_offset = 0
                
                # Set up parameters as local variables
                param_offset = 8
                for param in params:
                    self.variables[param.value] = param_offset
                    param_offset += 4
                
                self.codegen(node.children[0])
                self.generated_text_asm += "mov esp, ebp\npop ebp\nret\n"
                
                self.stack_offset = old_stack_offset
                self.variables = old_variables
        elif node.type == 'Block':
            for statement in node.children:
                self.codegen(statement)
        elif node.type == 'VariableDeclaration':
            var_name = node.value
            self.stack_offset += 4
            self.variables[var_name] = -self.stack_offset
            
            # Generate code for the expression
            self.codegen(node.children[0])
            
            # Store result in variable
            self.generated_text_asm += f"sub esp, 4\nmov dword [ebp{self.variables[var_name]}], eax\n"
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
            
            # Generate code to get the variable value
            self.codegen(var_expr)
            self.generated_text_asm += "push eax\n"  # Save the string pointer
            
            for i, case in enumerate(node.children[1:]):
                next_case_label = self.get_unique_label(f"next_case_{i}")
                
                # Create string literal for comparison
                case_str_label = self.get_unique_label("case_str")
                
                # Convert case value to null-terminated string
                case_string = f'"{case.value}",0'
                self.generated_data_asm += f"{case_str_label}: db {case_string}\n"
                
                # Compare strings
                self.generated_text_asm += f"mov eax, [esp]\n"  # Get saved string pointer
                self.generated_text_asm += f"push dword {case_str_label}\n"
                self.generated_text_asm += f"push eax\n"
                self.generated_text_asm += f"call string_compare\n"
                self.generated_text_asm += f"add esp, 8\n"
                self.generated_text_asm += f"test eax, eax\n"
                self.generated_text_asm += f"jz {next_case_label}\n"
                
                # Execute case action - clean up stack first
                self.generated_text_asm += f"add esp, 4\n"  # Remove saved pointer
                self.codegen(case.children[0])
                self.generated_text_asm += f"jmp {end_label}\n"
                
                self.generated_text_asm += f"{next_case_label}:\n"
            
            # Clean up stack if no match
            self.generated_text_asm += f"add esp, 4\n"
            self.generated_text_asm += f"{end_label}:\n"
        elif node.type == 'BinaryOp':
            self.codegen(node.children[0])
            self.generated_text_asm += "push eax\n"
            self.codegen(node.children[1])
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
            elif node.value == 'GREATER':
                self.generated_text_asm += "cmp eax, ebx\nsetg al\nmovzx eax, al\n"
            elif node.value == 'GREATER_EQUAL':
                self.generated_text_asm += "cmp eax, ebx\nsetge al\nmovzx eax, al\n"
            elif node.value == 'LESS':
                self.generated_text_asm += "cmp eax, ebx\nsetl al\nmovzx eax, al\n"
            elif node.value == 'LESS_EQUAL':
                self.generated_text_asm += "cmp eax, ebx\nsetle al\nmovzx eax, al\n"
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
                self.generated_text_asm += f"mov eax, dword [ebp{offset:+d}]\n"
            else:
                raise Exception(f"Undefined variable: {node.value}")
        elif node.type == 'StringLiteral':
            # Create a string in the data section
            string_label = self.get_unique_label("str")
            # Convert string to bytes, handling escape sequences
            char_bytes = []
            value = node.value.strip('"')  # Remove surrounding quotes if present
            i = 0
            while i < len(value):
                char = value[i]
                if char == '\\' and i + 1 < len(value):
                    next_char = value[i + 1]
                    if next_char == 'n':
                        char_bytes.append('10')  # newline
                        i += 2
                        continue
                    elif next_char == 't':
                        char_bytes.append('9')   # tab
                        i += 2
                        continue
                    elif next_char == '\\':
                        char_bytes.append('92')  # backslash
                        i += 2
                        continue
                    elif next_char == '"':
                        char_bytes.append('34')  # quote
                        i += 2
                        continue
                
                if char == "'":
                    char_bytes.append('39')
                elif ord(char) >= 32 and ord(char) <= 126:
                    char_bytes.append(f"'{char}'")
                else:
                    char_bytes.append(str(ord(char)))
                i += 1
            
            char_bytes.append('0')  # null terminator
            char_string = ', '.join(char_bytes)
            
            self.generated_data_asm += f"{string_label}: db {char_string}\n"
            self.generated_text_asm += f"mov eax, {string_label}\n"
        elif node.type == 'FunctionCall':
            command_name = node.value
            
            # Try to load command from commands subfolder
            command_module = self.load_command(command_name)
            if command_module and hasattr(command_module, 'compile'):
                try:
                    # Prepare arguments for command
                    command_args = []
                    for arg in node.children:
                        # Create a simple argument object
                        class SimpleArg:
                            def __init__(self, arg_node, compiler_ref):
                                self.type = arg_node.type
                                self.value = arg_node.value
                                if arg_node.type == 'Variable' and arg_node.value in compiler_ref.variables:
                                    offset = compiler_ref.variables[arg_node.value]
                                    self.asm = f"[ebp{offset:+d}]"
                                elif arg_node.type == 'Number':
                                    self.asm = str(arg_node.value)
                                else:
                                    self.asm = "eax"  # Default
                        
                        command_args.append(SimpleArg(arg, self))
                    
                    result = command_module.compile(command_args)
                    if result:
                        self.generated_data_asm += result.get("data", "")
                        self.generated_text_asm += result.get("text", "")
                        if "bss" in result:
                            self.generated_bss_asm += result.get("bss", "")
                except Exception as e:
                    print(f"Warning: Error compiling command '{command_name}': {e}")
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
        elif node.type == 'ReturnStatement':
            if node.children:
                self.codegen(node.children[0])
            # eax already contains the return value
            self.generated_text_asm += "mov esp, ebp\npop ebp\nret\n"

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source_file.rx>")
        sys.exit(1)
        
    source_file = sys.argv[1]
    try:
        compiler = Compiler(source_file)
        compiler.run()
    except Exception as e:
        print(f"Compilation error: {e}")
        sys.exit(1)