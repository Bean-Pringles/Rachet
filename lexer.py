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
        # Corrected patterns and their order of precedence
        patterns = [
            # Keywords and symbols first to prevent greedy matches
            (r'\buse\b', 'USE'),
            (r'\b(crate)\b', 'CRATE'),
            (r'\b(fn)\b', 'FN'),
            (r'\b(main)\b', 'MAIN'),
            (r'\b(iso|bin)\b', 'CRATE_NAME'), # A specific token for ISO/BIN
            (r'\b(shutdown)\b', 'IDENTIFIER_ARG'),
            
            # Operators
            (r'::', 'DOUBLE_COLON'),
            
            # Delimiters and symbols
            (r'\(', 'LPAREN'),
            (r'\)', 'RPAREN'),
            (r'\{', 'LBRACE'),
            (r'\}', 'RBRACE'),
            (r';', 'SEMICOLON'),
            
            # Literals
            (r'"(.*?)"', 'STRING_LITERAL'),
            
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
    source = 'use crate::iso; fn main() { print("Hello World!"); os(shutdown); }'
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    print(tokens)