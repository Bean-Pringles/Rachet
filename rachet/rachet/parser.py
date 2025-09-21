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
                raise Exception(f"Unexpected token: {self.current_token().type}")
        return ast

    def current_token(self):
        if self.position >= len(self.tokens):
            raise Exception(f"Unexpected end of file at position {self.position}")
        return self.tokens[self.position]

    def peek_token(self, offset=1):
        """Look ahead at the next token without advancing"""
        pos = self.position + offset
        if pos >= len(self.tokens):
            return None
        return self.tokens[pos]

    def advance(self):
        self.position += 1

    def expect(self, token_type):
        if self.position >= len(self.tokens):
            raise Exception(f"Expected token type '{token_type}', but reached end of file")
        if self.current_token().type == token_type:
            self.advance()
        else:
            current = self.current_token()
            raise Exception(f"Expected token type '{token_type}', but got '{current.type}' with value '{current.value}' at position {self.position}")

    def parse_use_statement(self):
        self.expect('USE')
        self.expect('CRATE')
        self.expect('DOUBLE_COLON')
        target = self.current_token().value
        self.advance()
        self.expect('SEMICOLON')
        return Node('UseStatement', target)

    def parse_function_declaration(self):
        self.expect('FN')
        name = self.current_token().value
        if name == 'main':
            self.expect('MAIN')
        else:
            self.expect('IDENTIFIER')
        
        self.expect('LPAREN')
        params = []
        while self.current_token().type != 'RPAREN':
            if self.current_token().type == 'IDENTIFIER':
                params.append(Node('Parameter', self.current_token().value))
                self.advance()
                if self.current_token().type == 'COMMA':
                    self.advance()
        self.expect('RPAREN')
        
        self.expect('LBRACE')
        body = self.parse_block()
        self.expect('RBRACE')
        return Node('FunctionDeclaration', name, [body] + params)

    def parse_block(self):
        statements = []
        while self.current_token().type != 'RBRACE':
            statements.append(self.parse_statement())
        return Node('Block', children=statements)

    def parse_statement(self):
        if self.current_token().type == 'LET':
            return self.parse_variable_declaration()
        elif self.current_token().type == 'IF':
            return self.parse_if_statement()
        elif self.current_token().type == 'MATCH':
            return self.parse_match_statement()
        elif self.current_token().type == 'RETURN':
            return self.parse_return_statement()
        elif self.current_token().type in ['IDENTIFIER', 'INPUT', 'OS']:
            # Check if it's a function call by looking ahead
            if self.position + 1 < len(self.tokens) and self.tokens[self.position + 1].type == 'LPAREN':
                return self.parse_function_call()
            else:
                raise Exception(f"Unexpected identifier: {self.current_token().value} at position {self.position}")
        else:
            raise Exception(f"Unexpected statement: {self.current_token().type} at position {self.position}")

    def parse_variable_declaration(self):
        self.expect('LET')
        name = self.current_token().value
        self.expect('IDENTIFIER')
        
        var_type = None
        if self.current_token().type == 'COLON':
            self.advance()
            var_type = self.current_token().value
            self.expect('TYPE')
        
        self.expect('ASSIGN')
        value = self.parse_expression()
        self.expect('SEMICOLON')
        
        var_node = Node('VariableDeclaration', name, [value])
        if var_type:
            var_node.children.append(Node('Type', var_type))
        return var_node

    def parse_if_statement(self):
        self.expect('IF')
        self.expect('LPAREN')
        condition = self.parse_expression()
        self.expect('RPAREN')
        self.expect('LBRACE')
        then_block = self.parse_block()
        self.expect('RBRACE')
        
        else_block = None
        if self.position < len(self.tokens) and self.current_token().type == 'ELSE':
            self.advance()
            if self.current_token().type == 'IF':
                else_block = self.parse_if_statement()
            else:
                self.expect('LBRACE')
                else_block = self.parse_block()
                self.expect('RBRACE')
        
        children = [condition, then_block]
        if else_block:
            children.append(else_block)
        return Node('IfStatement', children=children)

    def parse_match_statement(self):
        self.expect('MATCH')
        self.expect('LPAREN')
        expr = self.parse_expression()
        self.expect('RPAREN')
        self.expect('LBRACE')
        
        cases = []
        while self.current_token().type != 'RBRACE':
            case_value = self.current_token().value.strip('"')
            self.advance()
            self.expect('COMMA')
            
            if self.current_token().type == 'RETURN':
                self.advance()
                action = self.parse_expression()
            else:
                action = self.parse_statement()
            
            cases.append(Node('MatchCase', case_value, [action]))
            
            if self.current_token().type == 'SEMICOLON':
                self.advance()
        
        self.expect('RBRACE')
        return Node('MatchStatement', children=[expr] + cases)

    def parse_return_statement(self):
        self.expect('RETURN')
        value = self.parse_expression()
        return Node('ReturnStatement', children=[value])

    def parse_expression(self):
        return self.parse_logical_or()

    def parse_logical_or(self):
        left = self.parse_logical_and()
        while self.position < len(self.tokens) and self.current_token().type == 'OR':
            op = self.current_token().type
            self.advance()
            right = self.parse_logical_and()
            left = Node('BinaryOp', op, [left, right])
        return left

    def parse_logical_and(self):
        left = self.parse_equality()
        while self.position < len(self.tokens) and self.current_token().type == 'AND':
            op = self.current_token().type
            self.advance()
            right = self.parse_equality()
            left = Node('BinaryOp', op, [left, right])
        return left

    def parse_equality(self):
        left = self.parse_unary()
        while self.position < len(self.tokens) and self.current_token().type in ['EQUAL', 'NOT_EQUAL']:
            op = self.current_token().type
            self.advance()
            right = self.parse_unary()
            left = Node('BinaryOp', op, [left, right])
        return left

    def parse_unary(self):
        """Handle unary operators like 'not'"""
        if self.current_token().type == 'NOT':
            op = self.current_token().type
            self.advance()
            expr = self.parse_arithmetic()
            return Node('UnaryOp', op, [expr])
        return self.parse_arithmetic()

    def parse_arithmetic(self):
        left = self.parse_term()
        while self.position < len(self.tokens) and self.current_token().type in ['PLUS', 'MINUS']:
            op = self.current_token().type
            self.advance()
            right = self.parse_term()
            left = Node('BinaryOp', op, [left, right])
        return left

    def parse_term(self):
        left = self.parse_primary()
        while self.position < len(self.tokens) and self.current_token().type in ['MULTIPLY', 'DIVIDE']:
            op = self.current_token().type
            self.advance()
            right = self.parse_primary()
            left = Node('BinaryOp', op, [left, right])
        return left

    def parse_primary(self):
        if self.current_token().type == 'NUMBER':
            value = int(self.current_token().value)
            self.advance()
            return Node('Number', value)
        elif self.current_token().type == 'STRING_LITERAL':
            value = self.current_token().value
            self.advance()
            return Node('StringLiteral', value)
        elif self.current_token().type in ['IDENTIFIER', 'INPUT', 'OS']:
            # Check if it's a function call
            if self.position + 1 < len(self.tokens) and self.tokens[self.position + 1].type == 'LPAREN':
                return self.parse_function_call()
            else:
                value = self.current_token().value
                self.advance()
                return Node('Variable', value)
        elif self.current_token().type == 'LPAREN':
            self.advance()
            expr = self.parse_expression()
            self.expect('RPAREN')
            return expr
        else:
            raise Exception(f"Unexpected token in expression: {self.current_token().type}")

    def parse_function_call(self):
        name = self.current_token().value
        if self.current_token().type == 'IDENTIFIER':
            self.expect('IDENTIFIER')
        elif self.current_token().type == 'INPUT':
            self.expect('INPUT')
        elif self.current_token().type == 'OS':
            self.expect('OS')
        
        self.expect('LPAREN')
        args = []
        
        # Handle special case for os(shutdown) without quotes
        if name == 'os' and self.current_token().type == 'SHUTDOWN':
            args.append(Node('StringLiteral', '"shutdown"'))
            self.advance()
        else:
            while self.current_token().type != 'RPAREN':
                args.append(self.parse_expression())
                if self.current_token().type == 'COMMA':
                    self.advance()
        
        self.expect('RPAREN')
        # Expect semicolon for function call statements
        if self.position < len(self.tokens) and self.current_token().type == 'SEMICOLON':
            self.advance()
        return Node('FunctionCall', name, args)

if __name__ == '__main__':
    # Test the parser with a simple example
    from lexer import Lexer
    source = 'let x = 5 + 3; print("test");'
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(ast)