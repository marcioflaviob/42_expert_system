#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


Truth = Optional[bool]



######## IDEAS ################

class Letter:
    char: str
    value: Truth
    queried: bool

################################

@dataclass(frozen=True)
class Rule:
	left: tuple
	right: tuple


def strip_comment(line: str) -> str:
	return line.split("#", 1)[0].strip()


def tokenize_expression(expr: str) -> List[str]:
	tokens: List[str] = []
	for char in expr.replace(" ", ""):
		if char.isupper() or char in {"!", "+", "|", "^", "(", ")"}:
			tokens.append(char)
		else:
			raise ValueError(f"Invalid character in expression: {char}")
	return tokens


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

	def parse(self) -> Tuple:
		node = self.parse_xor()
		if self.current() is not None:
			raise ValueError(f"Unexpected token: {self.current()}")
		return node

	def parse_xor(self) -> Tuple:
		node = self.parse_or()
		while self.current() == "^":
			self.consume("^")
			node = ("XOR", node, self.parse_or())
		return node

	def parse_or(self) -> Tuple:
		node = self.parse_and()
		while self.current() == "|":
			self.consume("|")
			node = ("OR", node, self.parse_and())
		return node

	def parse_and(self) -> Tuple:
		node = self.parse_not()
		while self.current() == "+":
			self.consume("+")
			node = ("AND", node, self.parse_not())
		return node

	def parse_not(self) -> Tuple:
		if self.current() == "!":
			self.consume("!")
			return ("NOT", self.parse_not())
		return self.parse_primary()

	def parse_primary(self) -> Tuple:
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


def parse_expression(expr: str) -> Tuple:
	tokens = tokenize_expression(expr)
	if not tokens:
		raise ValueError("Empty expression")
	return ExpressionParser(tokens).parse()


def parse_literal_list(payload: str) -> Tuple[Set[str], Set[str]]:
	positives: Set[str] = set()
	negatives: Set[str] = set()
	compact = payload.replace(" ", "")
	idx = 0
	while idx < len(compact):
		if compact[idx] == "!":
			idx += 1
			if idx >= len(compact) or not compact[idx].isupper():
				raise ValueError("Invalid negated fact/query")
			negatives.add(compact[idx])
			idx += 1
			continue
		if compact[idx].isupper():
			positives.add(compact[idx])
			idx += 1
			continue
		raise ValueError(f"Invalid symbol in facts/queries: {compact[idx]}")
	return positives, negatives


def extract_entailed_literals(expr: Tuple) -> Set[Tuple[str, bool]]:
	node_type = expr[0]
	if node_type == "VAR":
		return {(expr[1], True)}
	if node_type == "NOT" and expr[1][0] == "VAR":
		return {(expr[1][1], False)}
	if node_type == "AND":
		return extract_entailed_literals(expr[1]) | extract_entailed_literals(expr[2])
	return set()


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


class BackwardChainer:
	def __init__(self, rules: List[Rule], true_facts: Set[str], false_facts: Set[str]):
		self.rules = rules
		self.true_facts = set(true_facts)
		self.false_facts = set(false_facts)
		self.targets: Dict[Tuple[str, bool], List[Rule]] = {}
		self.memo_status: Dict[str, Truth] = {}
		self.memo_proof: Dict[Tuple[str, bool], bool] = {}

		for rule in self.rules:
			for literal in extract_entailed_literals(rule.right):
				self.targets.setdefault(literal, []).append(rule)

	def evaluate_expression(self, expr: Tuple, stack: Set[Tuple[str, bool]]) -> Truth:
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
		raise ValueError(f"Unknown Tuple node type: {node_type}")

	def prove_literal(self, symbol: str, desired_truth: bool, stack: Set[Tuple[str, bool]]) -> bool:
		key = (symbol, desired_truth)
		if key in self.memo_proof:
			return self.memo_proof[key]
		if key in stack:
			return False

		if desired_truth and symbol in self.true_facts:
			self.memo_proof[key] = True
			return True
		if not desired_truth and symbol in self.false_facts:
			self.memo_proof[key] = True
			return True

		stack.add(key)
		proven = False
		for rule in self.targets.get(key, []):
			result = self.evaluate_expression(rule.left, stack)
			if result is True:
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

		if can_be_true and can_be_false:
			status = None
		elif can_be_true:
			status = True
		elif can_be_false:
			status = False
		else:
			status = None

		self.memo_status[symbol] = status
		return status


def parse_knowledge_base(file_path: Path) -> Tuple[List[Rule], Set[str], Set[str], List[str]]:
	rules: List[Rule] = []
	true_facts: Set[str] = set()
	false_facts: Set[str] = set()
	queries: List[str] = []

	for raw_line in file_path.read_text(encoding="utf-8").splitlines():
		line = strip_comment(raw_line)
		if not line:
			continue

		if "<=>" in line:
			left_text, right_text = [part.strip() for part in line.split("<=>", 1)]
			left_expr = parse_expression(left_text)
			right_expr = parse_expression(right_text)
			rules.append(Rule(left=left_expr, right=right_expr))
			rules.append(Rule(left=right_expr, right=left_expr))
			continue

		if "=>" in line:
			left_text, right_text = [part.strip() for part in line.split("=>", 1)]
			rules.append(Rule(left=parse_expression(left_text), right=parse_expression(right_text)))
			continue

		if line.startswith("="):
			positives, negatives = parse_literal_list(line[1:])
			true_facts |= positives
			false_facts |= negatives
			continue

		if line.startswith("?"):
			positives, negatives = parse_literal_list(line[1:])
			if negatives:
				raise ValueError("Queries must be positive symbols")
			queries.extend(sorted(positives))
			continue

		raise ValueError(f"Unrecognized line: {line}")

	return rules, true_facts, false_facts, queries


def format_truth(value: Truth) -> str:
	if value is True:
		return "TRUE"
	if value is False:
		return "FALSE"
	return "UNDETERMINED"


def main() -> None:
	parser = argparse.ArgumentParser(description="Backward-chaining expert system")
	parser.add_argument("input_file", nargs="?", default="easy.txt", help="Path to knowledge base file")
	args = parser.parse_args()

	rules, true_facts, false_facts, queries = parse_knowledge_base(Path(args.input_file))
	chainer = BackwardChainer(rules, true_facts, false_facts)

	for symbol in queries:
		print(f"{symbol}: {format_truth(chainer.get_symbol_status(symbol))}")


if __name__ == "__main__":
	main()
