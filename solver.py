from parser import Letter, Truth, ParsedData
from typing import Dict, List, Optional, Set


def apply_op(op: str, a: Truth, b: Truth) -> Truth:
    if op == '+':
        if a is False or b is False:
            return False
        if a is True and b is True:
            return True
        return None
    elif op == '|':
        if a is True or b is True:
            return True
        if a is False and b is False:
            return False
        return None
    elif op == '^':
        if a is None or b is None:
            return None
        return bool(a) != bool(b)
    raise ValueError(f"Unknown operator: {op}")


def evaluate_side(tokens: List[str], parsed: ParsedData, visited: Set[str]) -> Truth:
    """Evaluate an expression token list, recursively proving unknown letters."""
    result: Truth = None
    op: Optional[str] = None
    negate_next = False
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token == '!':
            negate_next = True
            i += 1
            continue

        if token in ('+', '|', '^'):
            op = token
            i += 1
            continue

        if token == '(':
            depth = 1
            j = i + 1
            while j < len(tokens) and depth > 0:
                if tokens[j] == '(':
                    depth += 1
                elif tokens[j] == ')':
                    depth -= 1
                j += 1
            val = evaluate_side(tokens[i + 1:j - 1], parsed, visited)
            if negate_next:
                val = (not val) if val is not None else None
                negate_next = False
            if result is None:
                result = val
            else:
                result = apply_op(op, result, val)
                op = None
            i = j
            continue

        if token.isupper():
            val = prove(token, parsed, visited)
            if negate_next:
                val = (not val) if val is not None else None
                negate_next = False
            if result is None:
                result = val
            else:
                result = apply_op(op, result, val)
                op = None

        i += 1

    return result


def get_top_level_op(tokens: List[str]) -> Optional[str]:
    """Return the first binary operator at the outermost (depth 0) level."""
    depth = 0
    for token in tokens:
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif token in ('+', '|', '^') and depth == 0:
            return token
    return None


def char_value_from_right(tokens: List[str], char: str) -> Optional[bool]:
    """
    Given that the right side evaluates to True (rule fired), return the value
    that `char` must take, or None if it cannot be determined.

    Derivation is only possible when the top-level connective is AND (+) or
    the expression is a single literal — every conjunct must individually be
    True (or False if negated).  OR / XOR at the top level leaves individual
    values ambiguous.
    """
    top_op = get_top_level_op(tokens)
    if top_op in ('|', '^'):
        return None

    # top_op is '+' or None: scan top-level tokens for `char`
    depth = 0
    negate_next = False
    for token in tokens:
        if token == '(':
            depth += 1
            negate_next = False
            continue
        if token == ')':
            depth -= 1
            continue
        if depth > 0:
            continue
        if token == '!':
            negate_next = True
            continue
        if token in ('+', '|', '^'):
            negate_next = False
            continue
        if token == char:
            return False if negate_next else True
        negate_next = False

    return None  # char not found at top level


def prove(char: str, parsed: ParsedData, visited: Set[str]) -> Truth:
    """
    Backward chaining: determine the truth value of `char`.

    1. Return immediately if value is already known.
    2. Detect cycles via `visited`; return False if caught in one.
    3. For every rule whose right side mentions `char`:
       - Evaluate the left side recursively.
       - If the left fires and char's value is derivable → return it.
       - If the left fires but char is in an OR/XOR (ambiguous) → Undetermined.
    4. If no rule involving char ever fired → closed-world assumption → False.
    """
    letter = Letter.get(char, parsed)

    if letter.value is not None:
        return letter.value

    if char in visited:
        return False  # cycle — cannot prove

    new_visited = visited | {char}
    rule_fired_ambiguously = False

    for rule in parsed.rules:
        if char not in rule.right.expression:
            continue  # char not mentioned in this rule's right side

        char_val = char_value_from_right(rule.right.expression, char)
        left_value = evaluate_side(rule.left.expression, parsed, new_visited)

        if left_value is True:
            if char_val is not None:
                letter.value = char_val
                return char_val
            else:
                rule_fired_ambiguously = True  # fired but can't pin down char

    if rule_fired_ambiguously:
        return None  # undetermined — letter.value stays None

    # Closed-world assumption: no rule involving char ever fired → False
    letter.value = False
    return False


def solve(parsed: ParsedData) -> Dict[str, Truth]:
    results = {}
    for char, letter in parsed.letters_by_char.items():
        if letter.queried:
            value = prove(char, parsed, set())
            results[char] = value
            label = "True" if value is True else "False" if value is False else "Undetermined"
            print(f"{char}: {label}")
    return results
