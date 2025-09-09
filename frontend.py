#!/usr/bin/env python3
"""
Rachet Language Frontend
Parses .rachet source files and outputs JSON tokens for the Rust compiler.
"""

import sys
import json
import re
from typing import List, Dict, Any, Optional


class RachetToken:
    """Represents a parsed token from Rachet source code."""
    
    def __init__(self, command: str, args: List[str], line: int):
        self.command = command
        self.args = args
        self.line = line
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "line": self.line
        }


class RachetParser:
    """Parser for the Rachet programming language."""
    
    def __init__(self):
        self.tokens: List[RachetToken] = []
    
    def parse_file(self, filename: str) -> List[RachetToken]:
        """Parse a .rachet file and return tokens."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{filename}': {e}", file=sys.stderr)
            sys.exit(1)
        
        self.tokens = []
        for line_num, line in enumerate(lines, 1):
            self._parse_line(line.strip(), line_num)
        
        return self.tokens
    
    def _parse_line(self, line: str, line_num: int) -> None:
        """Parse a single line of Rachet code."""
        # Skip empty lines
        if not line:
            return
        
        # Skip comments (lines starting with #)
        if line.startswith('#'):
            return
        
        # Tokenize the line
        tokens = self._tokenize_line(line)
        if not tokens:
            return
        
        command = tokens[0]
        args = tokens[1:]
        
        # Create and store the token
        rachet_token = RachetToken(command, args, line_num)
        self.tokens.append(rachet_token)
    
    def _tokenize_line(self, line: str) -> List[str]:
        """Tokenize a line, handling quoted strings properly."""
        tokens = []
        current_token = ""
        in_quotes = False
        quote_char = None
        i = 0
        
        while i < len(line):
            char = line[i]
            
            if not in_quotes:
                if char in ['"', "'"]:
                    # Start of quoted string
                    in_quotes = True
                    quote_char = char
                    current_token += char
                elif char.isspace():
                    # End of current token
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            else:
                # Inside quotes
                if char == quote_char:
                    # Check if it's escaped
                    if i > 0 and line[i-1] == '\\':
                        current_token += char
                    else:
                        # End of quoted string
                        current_token += char
                        in_quotes = False
                        quote_char = None
                else:
                    current_token += char
            
            i += 1
        
        # Add final token if exists
        if current_token:
            tokens.append(current_token)
        
        # Clean up quoted strings (remove outer quotes)
        cleaned_tokens = []
        for token in tokens:
            if ((token.startswith('"') and token.endswith('"')) or
                (token.startswith("'") and token.endswith("'"))):
                # Remove quotes and handle escape sequences
                cleaned_token = token[1:-1]
                cleaned_token = cleaned_token.replace('\\"', '"')
                cleaned_token = cleaned_token.replace("\\'", "'")
                cleaned_token = cleaned_token.replace('\\\\', '\\')
                cleaned_tokens.append(cleaned_token)
            else:
                cleaned_tokens.append(token)
        
        return cleaned_tokens
    
    def output_json(self) -> None:
        """Output tokens as JSON to stdout."""
        token_dicts = [token.to_dict() for token in self.tokens]
        json.dump(token_dicts, sys.stdout, indent=2)


def main():
    """Main entry point for the Rachet frontend."""
    if len(sys.argv) != 2:
        print("Usage: python frontend.py <source_file.rachet>", file=sys.stderr)
        sys.exit(1)
    
    source_file = sys.argv[1]
    
    # Validate file extension
    if not source_file.endswith('.rachet'):
        print(f"Warning: File '{source_file}' doesn't have .rachet extension", file=sys.stderr)
    
    # Parse and output
    parser = RachetParser()
    parser.parse_file(source_file)
    parser.output_json()


if __name__ == "__main__":
    main()