from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


Truth = Optional[bool]


@dataclass(frozen=True)
class Rule:
	left: tuple
	right: tuple

class Letter:
    char: str
    value: Truth
    queried: bool

def remove_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()

def remove_whitespace(line: str) -> str:
    return line.replace(" ", "")

def tokenize_expression(line: str) -> bool:
    for char in line:
        if not (char.isupper() or char in {"!", "+", "|", "^", "(", ")"}):
            return False
    return True

