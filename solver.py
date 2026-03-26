from pathlib import Path
from logic import xor, and_op, or_op, not_op
from parser import Rule, Letter, Truth, read_file, ParsedData, Side
from typing import Dict, List, Optional, Set, Tuple

def find_query_left_side(parsed: ParsedData, letter: Letter) -> Optional[Side]:
    for rule in parsed.rules:
        if letter.char in rule.right.expression and not rule.right.checked:
            return rule.left
    return None

def operate(op: Optional[str], a: Truth, b: Truth) -> Truth:
    if op == "+":
        return and_op(Letter(char="", value=a, queried=False), Letter(char="", value=b, queried=False))
    elif op == "|":
        return or_op(Letter(char="", value=a, queried=False), Letter(char="", value=b, queried=False))
    elif op == "^":
        return xor(Letter(char="", value=a, queried=False), Letter(char="", value=b, queried=False))
    else:
        raise ValueError(f"Invalid operator: {op}")

def solve_side(parsed: ParsedData, side: Side) -> Optional[Truth]:
    a: Optional[Tuple[Truth, bool]] = None, False
    b: Optional[Tuple[Truth, bool]] = None, False
    op: Optional[str] = None
    for token in side.expression:
        if token.isupper():
            if a[1] is True and op is None:
                raise ValueError(f"Invalid expression: {side.expression}")
            letter = Letter.get(token, parsed)
            if a[1] is False:
                a = letter.value, True
            else:
                b = letter.value, True
                result: Optional[Truth] = operate(op, a[0], b[0])
                a = result, True
                b = None, False
                op = None
        elif not token.isupper():
            if a[1] is False:
                raise ValueError(f"Invalid expression: {side.expression}")
            op = token
            continue
        else:
            raise ValueError(f"Invalid token in expression: {token}")
    return a[0]

def solve(parsed: ParsedData) -> Dict[str, Truth]:
    for rule in parsed.rules:
        if rule.left.value is not None:
            continue
        result = solve_side(parsed, rule.left)
        if result is not None:
            rule.left.value = result
            rule.left.checked = True
    
    for rule in parsed.rules:
        print(f"{rule.left.expression} = {rule.left.value} (checked: {rule.left.checked}) => {rule.right.expression} = {rule.right.value} (checked: {rule.right.checked})")
    
    return {}