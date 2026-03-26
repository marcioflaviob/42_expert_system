from pathlib import Path
from parser import Rule, Letter, Truth, read_file, ParsedData, Side
from typing import Dict, List, Optional, Set, Tuple

def find_query_left_side(parsed: ParsedData, letter: Letter) -> Optional[Side]:
    for rule in parsed.rules:
        if letter.char in rule.right.expression and not rule.right.checked:
            return rule.left
    return None



def solve(parsed: ParsedData) -> Dict[str, Truth]:
    
    return {}