import re

class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"

class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []
        self.position = 0

    def tokenize(self):
        patterns = [
            # Keywords first to prevent greedy matches
            (r'\buse\b', 'USE'),
            (r'\b(crate)\b', 'CRATE'),
            (r'\b(fn)\b', 'FN'),
            (r'\b(main)\b', 'MAIN'),
            (r'\b(let)\b', 'LET'),
            (r'\b(if)\b', 'IF'),
            (r'\b(else)\b', 'ELSE'),
            (r'\b(match)\b', 'MATCH'),
            (r'\b(return)\b', 'RETURN'),
            (r'\b(not)\b', 'NOT'),  # Added NOT keyword
            (r'\b(input)\b', 'INPUT'),  # Added INPUT keyword
            (r'\b(os)\b', 'OS'),  # Added OS keyword
            (r'\b(shutdown)\b', 'SHUTDOWN'),  # Added SHUTDOWN keyword
            (r'\b(i32|string)\b', 'TYPE'),
            (r'\b(iso|bin)\b', 'CRATE_NAME'),
            
            # Operators and comparisons
            (r'::', 'DOUBLE_COLON'),
            (r'==', 'EQUAL'),
            (r'!=', 'NOT_EQUAL'),
            (r'&&', 'AND'),
            (r'\|\|', 'OR'),
            (r'=', 'ASSIGN'),
            (r'\+', 'PLUS'),
            (r'-', 'MINUS'),
            (r'\*', 'MULTIPLY'),
            (r'/', 'DIVIDE'),
            (r':', 'COLON'),
            
            # Delimiters and symbols
            (r'\(', 'LPAREN'),
            (r'\)', 'RPAREN'),
            (r'\{', 'LBRACE'),
            (r'\}', 'RBRACE'),
            (r';', 'SEMICOLON'),
            (r',', 'COMMA'),
            
            # Literals
            (r'"(.*?)"', 'STRING_LITERAL'),
            (r'\b(\d+)\b', 'NUMBER'),
            
            # Comments
            (r'//.*', None),  # Ignore comments
            
            # Identifiers and whitespace last
            (r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', 'IDENTIFIER'),
            (r'\s+', None),  # Ignore whitespace
        ]

        while self.position < len(self.source_code):
            match = None
            for pattern, token_type in patterns:
                regex = re.compile(pattern)
                m = regex.match(self.source_code, self.position)
                if m:
                    value = m.group(1) if len(m.groups()) > 0 else m.group(0)
                    if token_type:
                        self.tokens.append(Token(token_type, value))
                    self.position = m.end(0)
                    match = True
                    break
            if not match:
                raise Exception(f"Illegal character at position {self.position}: '{self.source_code[self.position]}'")
        return self.tokens

if __name__ == '__main__':
    source = '''use crate::iso; 
    fn main() { 
        print("Hello World!"); 
        let x = 5 * 5; 
        let y: i32 = 4 / 2; 
        if (x == 25 && y == 2) { 
            print("Correct"); 
        } else if (x == 25 && not y == 2) { 
            print("Y is wrong"); 
            print(y); 
        } else { 
            print("What is this on"); 
        }
        let name = input("Name:");
        let gender: string = input("Gender:");
        nameFn(name);
        os(shutdown); 
    }'''
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    for token in tokens:
        print(token)