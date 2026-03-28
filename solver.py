from parser import ParsedData, Truth
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

Expression = Tuple


class ContradictionError(Exception):
    pass


class ExpressionParser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.position = 0

    def current(self) -> Optional[str]:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def consume(self, token: str) -> None:
        if self.current() != token:
            raise ValueError(f"Expected '{token}', found '{self.current()}'")
        self.position += 1

    def parse(self) -> Expression:
        node = self.parse_xor()
        if self.current() is not None:
            raise ValueError(f"Unexpected token: {self.current()}")
        return node

    def parse_xor(self) -> Expression:
        node = self.parse_or()
        while self.current() == "^":
            self.consume("^")
            node = ("XOR", node, self.parse_or())
        return node

    def parse_or(self) -> Expression:
        node = self.parse_and()
        while self.current() == "|":
            self.consume("|")
            node = ("OR", node, self.parse_and())
        return node

    def parse_and(self) -> Expression:
        node = self.parse_not()
        while self.current() == "+":
            self.consume("+")
            node = ("AND", node, self.parse_not())
        return node

    def parse_not(self) -> Expression:
        if self.current() == "!":
            self.consume("!")
            return ("NOT", self.parse_not())
        return self.parse_primary()

    def parse_primary(self) -> Expression:
        token = self.current()
        if token is None:
            raise ValueError("Unexpected end of expression")
        if token == "(":
            self.consume("(")
            node = self.parse_xor()
            self.consume(")")
            return node
        if token.isupper():
            self.position += 1
            return ("VAR", token)
        raise ValueError(f"Unexpected token in expression: {token}")


def parse_expression(tokens: List[str]) -> Expression:
    if not tokens:
        raise ValueError("Empty expression")
    return ExpressionParser(tokens).parse()


def tri_not(value: Truth) -> Truth:
    if value is None:
        return None
    return not value


def tri_and(left: Truth, right: Truth) -> Truth:
    if left is False or right is False:
        return False
    if left is True and right is True:
        return True
    return None


def tri_or(left: Truth, right: Truth) -> Truth:
    if left is True or right is True:
        return True
    if left is False and right is False:
        return False
    return None


def tri_xor(left: Truth, right: Truth) -> Truth:
    if left is None or right is None:
        return None
    return left != right


def extract_entailed_literals(expr: Expression) -> Set[Tuple[str, bool]]:
    node_type = expr[0]
    if node_type == "VAR":
        return {(expr[1], True)}
    if node_type == "NOT" and expr[1][0] == "VAR":
        return {(expr[1][1], False)}
    if node_type == "AND":
        return extract_entailed_literals(expr[1]) | extract_entailed_literals(expr[2])
    return set()


def extract_symbols(expr: Expression) -> Set[str]:
    node_type = expr[0]
    if node_type == "VAR":
        return {expr[1]}
    if node_type == "NOT":
        return extract_symbols(expr[1])
    if node_type in {"AND", "OR", "XOR"}:
        return extract_symbols(expr[1]) | extract_symbols(expr[2])
    return set()


def extract_ambiguous_rhs_symbols(expr: Expression) -> Set[str]:
    node_type = expr[0]
    if node_type in {"OR", "XOR"}:
        return extract_symbols(expr)
    if node_type == "AND":
        return extract_ambiguous_rhs_symbols(expr[1]) | extract_ambiguous_rhs_symbols(expr[2])
    if node_type == "NOT":
        return extract_ambiguous_rhs_symbols(expr[1])
    return set()


class BackwardChainer:
    def __init__(self, parsed: ParsedData):
        self.parsed = parsed
        self.targets: Dict[Tuple[str, bool], List[Expression]] = {}
        self.ambiguous_targets: Dict[str, List[Expression]] = {}
        self.memo_status: Dict[str, Truth] = {}
        self.memo_proof: Dict[Tuple[str, bool], bool] = {}
        self.proven_true_facts: Set[str] = {
            char for char, letter in parsed.letters_by_char.items() if letter.value is True
        }
        self.proven_false_facts: Set[str] = set()

        for rule in parsed.rules:
            left_expr = parse_expression(rule.left.expression)
            right_expr = parse_expression(rule.right.expression)
            for literal in extract_entailed_literals(right_expr):
                self.targets.setdefault(literal, []).append(left_expr)
            for symbol in extract_ambiguous_rhs_symbols(right_expr):
                self.ambiguous_targets.setdefault(symbol, []).append(left_expr)

    def has_active_ambiguity(self, symbol: str, stack: Set[Tuple[str, bool]]) -> bool:
        for left_expr in self.ambiguous_targets.get(symbol, []):
            if self.evaluate_expression(left_expr, stack) is True:
                return True
        return False

    def expression_to_str(self, expr: Expression) -> str:
        node_type = expr[0]
        if node_type == "VAR":
            return expr[1]
        if node_type == "NOT":
            child = self.expression_to_str(expr[1])
            if expr[1][0] == "VAR":
                return f"!{child}"
            return f"!({child})"
        if node_type == "AND":
            return f"({self.expression_to_str(expr[1])} + {self.expression_to_str(expr[2])})"
        if node_type == "OR":
            return f"({self.expression_to_str(expr[1])} | {self.expression_to_str(expr[2])})"
        if node_type == "XOR":
            return f"({self.expression_to_str(expr[1])} ^ {self.expression_to_str(expr[2])})"
        return "?"

    def evaluate_expression(self, expr: Expression, stack: Set[Tuple[str, bool]]) -> Truth:
        node_type = expr[0]
        if node_type == "VAR":
            return self.get_symbol_status(expr[1], stack)
        if node_type == "NOT":
            return tri_not(self.evaluate_expression(expr[1], stack))
        if node_type == "AND":
            left = self.evaluate_expression(expr[1], stack)
            right = self.evaluate_expression(expr[2], stack)
            return tri_and(left, right)
        if node_type == "OR":
            left = self.evaluate_expression(expr[1], stack)
            right = self.evaluate_expression(expr[2], stack)
            return tri_or(left, right)
        if node_type == "XOR":
            left = self.evaluate_expression(expr[1], stack)
            right = self.evaluate_expression(expr[2], stack)
            return tri_xor(left, right)
        raise ValueError(f"Unknown expression node type: {node_type}")

    def prove_literal(self, symbol: str, desired_truth: bool, stack: Set[Tuple[str, bool]]) -> bool:
        key = (symbol, desired_truth)
        if key in self.memo_proof:
            return self.memo_proof[key]
        if key in stack:
            return False

        if desired_truth and symbol in self.proven_true_facts:
            self.memo_proof[key] = True
            return True
        if not desired_truth and symbol in self.proven_false_facts:
            self.memo_proof[key] = True
            return True

        stack.add(key)
        proven = False
        for left_expr in self.targets.get(key, []):
            if self.evaluate_expression(left_expr, stack) is True:
                proven = True
                break
        stack.remove(key)

        self.memo_proof[key] = proven
        return proven

    def get_symbol_status(self, symbol: str, stack: Optional[Set[Tuple[str, bool]]] = None) -> Truth:
        if symbol in self.memo_status:
            return self.memo_status[symbol]

        local_stack = stack if stack is not None else set()
        can_be_true = self.prove_literal(symbol, True, local_stack)
        can_be_false = self.prove_literal(symbol, False, local_stack)
        has_ambiguity = self.has_active_ambiguity(symbol, local_stack)

        if can_be_true and can_be_false:
            raise ContradictionError(
                f"Contradiction detected: '{symbol}' can be proven both TRUE and FALSE"
            )
        elif can_be_true:
            status = True
        elif has_ambiguity:
            status = None
        elif can_be_false:
            status = False
        else:
            status = False

        self.memo_status[symbol] = status
        return status

    def build_query_explanation(self, symbol: str) -> str:
        lines: List[str] = []
        lines.append(f"Query: {symbol}")
        lines.append("-" * 72)

        final_status = self.get_symbol_status(symbol)
        if symbol in self.proven_true_facts:
            state: Truth = True
            lines.append(f"Initial state: {symbol} = {format_truth(state)} (initial fact)")
            lines.append("")
            lines.append("Symbol is already proven by initial facts; no rule testing is required.")
            lines.append(f"Final state: {symbol} = {format_truth(final_status)}")
            return "\n".join(lines)

        state = False
        lines.append(f"Initial state: {symbol} = {format_truth(state)} (default)")

        stack: Set[Tuple[str, bool]] = set()
        true_candidates = self.targets.get((symbol, True), [])
        if true_candidates:
            lines.append("")
            lines.append("Trying rules that could prove TRUE:")
            for index, left_expr in enumerate(true_candidates, start=1):
                left_result = self.evaluate_expression(left_expr, stack)
                lines.append(f"  [T{index}] Test: {self.expression_to_str(left_expr)} => {symbol}")
                lines.append(f"       Left result: {format_truth(left_result)}")
                if left_result is True:
                    state = True
                    lines.append(f"       State after rule: {symbol} = {format_truth(state)} (PROVEN)")
                    lines.append("")
                    lines.append(f"Final state: {symbol} = {format_truth(final_status)}")
                    return "\n".join(lines)
                lines.append(f"       State after rule: {symbol} = {format_truth(state)}")
        else:
            lines.append("")
            lines.append("No rules can directly prove this symbol as TRUE.")

        false_candidates = self.targets.get((symbol, False), [])
        if false_candidates:
            lines.append("")
            lines.append("Trying rules that could prove FALSE:")
            for index, left_expr in enumerate(false_candidates, start=1):
                left_result = self.evaluate_expression(left_expr, stack)
                lines.append(f"  [F{index}] Test: {self.expression_to_str(left_expr)} => !{symbol}")
                lines.append(f"       Left result: {format_truth(left_result)}")
                if left_result is True:
                    state = False
                    lines.append(f"       State after rule: {symbol} = {format_truth(state)} (PROVEN)")
                    lines.append("")
                    lines.append(f"Final state: {symbol} = {format_truth(final_status)}")
                    return "\n".join(lines)
                lines.append(f"       State after rule: {symbol} = {format_truth(state)}")

        ambiguity_candidates = self.ambiguous_targets.get(symbol, [])
        if ambiguity_candidates:
            lines.append("")
            lines.append("Checking OR/XOR ambiguity rules involving this symbol:")
            ambiguity_active = False
            for index, left_expr in enumerate(ambiguity_candidates, start=1):
                left_result = self.evaluate_expression(left_expr, stack)
                lines.append(f"  [A{index}] Test ambiguity source: {self.expression_to_str(left_expr)} => (... {symbol} ...)")
                lines.append(f"       Left result: {format_truth(left_result)}")
                if left_result is True:
                    ambiguity_active = True
                    state = None
                    lines.append(f"       State after rule: {symbol} = {format_truth(state)}")
                    break
                lines.append(f"       State after rule: {symbol} = {format_truth(state)}")

            if ambiguity_active:
                lines.append("")
                lines.append(f"Final state: {symbol} = {format_truth(final_status)}")
                return "\n".join(lines)

        lines.append("")
        lines.append("No testable rule proved a different value.")
        lines.append(f"Final state: {symbol} = {format_truth(final_status)}")
        return "\n".join(lines)


def format_truth(value: Truth) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return "UNDETERMINED"


def solve(parsed: ParsedData, explanation_file: Optional[Path] = None) -> Dict[str, Truth]:
    chainer = BackwardChainer(parsed)
    results: Dict[str, Truth] = {}

    queried_letters = sorted(
        char for char, letter in parsed.letters_by_char.items() if letter.queried
    )
    for char in queried_letters:
        value = chainer.get_symbol_status(char)
        results[char] = value
        print(f"{char}: {format_truth(value)}")

    if explanation_file is not None:
        blocks: List[str] = []
        blocks.append("EXPERT SYSTEM EXPLANATION REPORT")
        blocks.append("=" * 72)
        blocks.append("")
        for index, char in enumerate(queried_letters, start=1):
            blocks.append(f"[{index}] {char}")
            blocks.append(chainer.build_query_explanation(char))
            blocks.append("")
        explanation_file.write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")

    return results