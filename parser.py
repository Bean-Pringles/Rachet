class Node:
    def __init__(self, type, value=None, children=None):
        self.type = type
        self.value = value
        self.children = children if children is not None else []

    def __repr__(self):
        if self.children:
            return f"Node({self.type}, value={repr(self.value)}, children={self.children})"
        return f"Node({self.type}, value={repr(self.value)})"

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def parse(self):
        ast = Node('Program')
        while self.position < len(self.tokens):
            if self.current_token().type == 'USE':
                ast.children.append(self.parse_use_statement())
            elif self.current_token().type == 'FN':
                ast.children.append(self.parse_function_declaration())
            else:
                raise Exception("Unexpected token")
        return ast

    def current_token(self):
        return self.tokens[self.position]

    def advance(self):
        self.position += 1

    def expect(self, token_type):
        if self.current_token().type == token_type:
            self.advance()
        else:
            raise Exception(f"Expected token type '{token_type}', but got '{self.current_token().type}'")

    def parse_use_statement(self):
        self.expect('USE')
        self.expect('CRATE')
        self.expect('DOUBLE_COLON')
        target = self.current_token().value
        self.advance() # 'iso' or 'bin'
        self.expect('SEMICOLON')
        return Node('UseStatement', target)

    def parse_function_declaration(self):
        self.expect('FN')
        name = self.current_token().value
        self.expect('MAIN')
        self.expect('LPAREN')
        self.expect('RPAREN')
        self.expect('LBRACE')
        body = self.parse_block()
        self.expect('RBRACE')
        return Node('FunctionDeclaration', name, [body])

    def parse_block(self):
        statements = []
        while self.current_token().type != 'RBRACE':
            statements.append(self.parse_statement())
        return Node('Block', children=statements)

    def parse_statement(self):
        if self.current_token().type == 'IDENTIFIER':
            return self.parse_function_call()
        else:
            raise Exception("Unexpected statement")

    def parse_function_call(self):
        name = self.current_token().value
        self.expect('IDENTIFIER')
        self.expect('LPAREN')
        args = []
        while self.current_token().type != 'RPAREN':
            # Create a Node for each argument
            if self.current_token().type == 'STRING_LITERAL':
                args.append(Node('StringLiteral', self.current_token().value))
            elif self.current_token().type == 'IDENTIFIER_ARG':
                args.append(Node('IdentifierArg', self.current_token().value))
            else:
                raise Exception("Unexpected argument type")
            self.advance()
        self.expect('RPAREN')
        self.expect('SEMICOLON')
        return Node('FunctionCall', name, [Node('Arguments', children=args)])

if __name__ == '__main__':
    from lexer import Lexer
    source = 'use crate::iso; fn main() { print("Hello World!"); os(shutdown); }'
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(ast)