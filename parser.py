from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


Truth = Optional[bool]


@dataclass(frozen=True)
class Rule:
	left: List[str]
	right: List[str]

@dataclass
class Letter:
    char: str
    value: Truth
    queried: bool

    @classmethod
    def create(cls, char: str):
        if not char.isupper() or len(char) != 1:
            raise ValueError(f"Invalid letter: {char}")
        letter = letters_by_char.get(char)
        if letter is None:
            letter = Letter(char=char, value=False, queried=False)
            letters_by_char[char] = letter
            letters_in_order.append(letter)

    @classmethod
    def get(cls, char: str) -> Letter:
        letter = letters_by_char.get(char)
        if letter is None:
            raise ValueError(f"Letter not found: {char}")
        return letter
    
    @classmethod
    def set(cls, char: str, value: Truth, queried: bool = False) -> Letter:
        if not char.isupper() or len(char) != 1:
            raise ValueError(f"Invalid letter: {char}")
        letter = letters_by_char.get(char)
        if letter is None:
            raise ValueError(f"Letter not found: {char}")
        updated_letter = Letter(char=char, value=value, queried=queried)
        letters_by_char[char] = updated_letter
        return updated_letter

letters_by_char: Dict[str, Letter] = {}
letters_in_order: List[Letter] = []
rules: List[Rule] = []

def remove_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()

def remove_whitespace(line: str) -> str:
    return line.replace(" ", "")

def has_bad_parenthesis(tokens: List[str]) -> bool:
    if tokens.count("(") is not tokens.count(")"):
        return True
    return False

def tokenize_expression(line: str) -> List[str]:
    tokens: List[str] = []
    for char in line:
        if not (char.isupper() or char in {"!", "+", "|", "^", "(", ")"}):
            raise ValueError("Invalid character: " + char)
        if char.isupper():
            Letter.create(char)
        tokens.append(char)
    if not tokens:
        raise ValueError("Empty expression")
    if has_bad_parenthesis(tokens):
        raise ValueError("Mismatched parentheses")
    return tokens

def read_file(file_path: Path):
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = remove_comment(raw_line)
        line = remove_whitespace(line)
        if not line:
            continue
        if "=>" in line:
            left, right = line.split("=>", 1)
            rule = Rule(left=tokenize_expression(left), right=tokenize_expression(right))
            rules.append(rule)
        elif "<=>" in line:
            left, right = line.split("<=>", 1)
            rule = Rule(left=tokenize_expression(left), right=tokenize_expression(right))
            reversedRule = Rule(left=rule.right, right=rule.left)
            rules.append(rule)
            rules.append(reversedRule)
        elif line.startswith("="):
            parse_facts(line)
        elif line.startswith("?"):
            parse_queries(line)
        

def parse_facts(tokens: str):
    for token in tokens[1:]:  # Skip the '=' token
        if not token.isupper() or len(token) != 1:
            raise ValueError(f"Invalid fact: {token}")
        Letter.set(token, True)

def parse_queries(tokens: str):
    for token in tokens[1:]:  # Skip the '?' token
        if not token.isupper() or len(token) != 1:
            raise ValueError(f"Invalid query: {token}")
        letter = Letter.get(token)
        Letter.set(token, letter.value, queried=True)

