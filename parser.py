from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

Truth = Optional[bool]

@dataclass
class Side:
    expression: List[str]
    value: Truth
    checked: bool

@dataclass(frozen=True)
class Rule:
	left: Side 
	right: Side 

@dataclass
class ParsedData:
    letters_by_char: Dict[str, Letter]
    rules: List[Rule]

@dataclass
class Letter:
    char: str
    value: Truth
    queried: bool

    @classmethod
    def create(cls, char: str, parsed: ParsedData) -> None:
        if not char.isupper() or len(char) != 1:
            raise ValueError(f"Invalid letter: {char}")
        letter = parsed.letters_by_char.get(char)
        if letter is None:
            letter = Letter(char=char, value=None, queried=False)
            parsed.letters_by_char[char] = letter

    @classmethod
    def get(cls, char: str, parsed: ParsedData) -> Letter:
        letter = parsed.letters_by_char.get(char)
        if letter is None:
            raise ValueError(f"Letter not found: {char}")
        return letter
    
    @classmethod
    def set(cls, char: str, value: Truth, parsed: ParsedData, queried: bool = False) -> Letter:
        if not char.isupper() or len(char) != 1:
            raise ValueError(f"Invalid letter: {char}")
        letter = parsed.letters_by_char.get(char)
        if letter is None:
            raise ValueError(f"Letter not found: {char}")
        updated_letter = Letter(char=char, value=value, queried=queried)
        parsed.letters_by_char[char] = updated_letter
        return updated_letter

def remove_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()

def remove_whitespace(line: str) -> str:
    return line.replace(" ", "")

def has_bad_parenthesis(tokens: List[str]) -> bool:
    if tokens.count("(") is not tokens.count(")"):
        return True
    return False

def tokenize_expression(line: str, parsed: ParsedData) -> List[str]:
    tokens: List[str] = []
    for char in line:
        if not (char.isupper() or char in {"!", "+", "|", "^", "(", ")"}):
            raise ValueError("Invalid character: " + char)
        if char.isupper():
            Letter.create(char, parsed)
        tokens.append(char)
    if not tokens:
        raise ValueError("Empty expression")
    if has_bad_parenthesis(tokens):
        raise ValueError("Mismatched parentheses")
    return tokens

def read_file(file_path: Path) -> ParsedData:
    parsed = ParsedData(letters_by_char={}, rules=[])
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = remove_comment(raw_line)
        line = remove_whitespace(line)
        if not line:
            continue
        if "=>" in line:
            left, right = line.split("=>", 1)
            rule = Rule(left=Side(tokenize_expression(left, parsed), value=None, checked=False), right=Side(tokenize_expression(right, parsed), value=None, checked=False))
            parsed.rules.append(rule)
        elif "<=>" in line:
            left, right = line.split("<=>", 1)
            rule = Rule(left=Side(tokenize_expression(left, parsed), value=None, checked=False), right=Side(tokenize_expression(right, parsed), value=None, checked=False))
            reversedRule = Rule(left=rule.right, right=rule.left)
            parsed.rules.append(rule)
            parsed.rules.append(reversedRule)
        elif line.startswith("="):
            parse_facts(line, parsed)
        elif line.startswith("?"):
            parse_queries(line, parsed)

    return parsed

def parse_facts(tokens: str, parsed: ParsedData):
    for token in tokens[1:]:  # Skip the '=' token
        if not token.isupper() or len(token) != 1:
            raise ValueError(f"Invalid fact: {token}")
        Letter.set(token, True, parsed)

def parse_queries(tokens: str, parsed: ParsedData):
    for token in tokens[1:]:  # Skip the '?' token
        if not token.isupper() or len(token) != 1:
            raise ValueError(f"Invalid query: {token}")
        letter = Letter.get(token, parsed)
        Letter.set(token, letter.value, parsed, queried=True)

