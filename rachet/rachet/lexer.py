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
            (r'\b(not)\b', 'NOT'),
            (r'\b(input)\b', 'INPUT'),
            (r'\b(os)\b', 'OS'),
            (r'\b(print)\b', 'PRINT'),
            (r'\b(pause)\b', 'PAUSE'),
            (r'\b(shutdown)\b', 'SHUTDOWN'),
            (r'\b(i32|string|str)\b', 'TYPE'),
            (r'\b(iso|bin)\b', 'CRATE_NAME'),
            
            # Operators and comparisons (order matters - longer operators first)
            (r'::', 'DOUBLE_COLON'),
            (r'>=', 'GREATER_EQUAL'),
            (r'<=', 'LESS_EQUAL'),
            (r'==', 'EQUAL'),
            (r'!=', 'NOT_EQUAL'),
            (r'&&', 'AND'),
            (r'\|\|', 'OR'),
            (r'>', 'GREATER'),
            (r'<', 'LESS'),
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
            
            # Comments (changed from // to #)
            (r'#.*', None),  # Ignore comments
            
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
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            source = f.read()
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        for token in tokens:
            print(token)
    else:
        print("Usage: python lexer.py <source_file.rx>")