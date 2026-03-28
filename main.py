import json
from dataclasses import asdict
import argparse
from pathlib import Path
from solver import solve
from parser import read_file, ParsedData, Letter


def parse_modified_facts(raw: str) -> set[str]:
	allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
	if any(char not in allowed for char in raw):
		raise ValueError("Only uppercase letters A-Z and spaces are allowed.")
	letters = {char for char in raw if char.isupper()}
	return letters


def has_initial_true_facts(parsed: ParsedData) -> bool:
	return any(letter.value is True for letter in parsed.letters_by_char.values())


def prompt_modified_facts(no_facts_message: bool = False) -> set[str] | None:
	if no_facts_message:
		print("No initial true facts were found in the input file.")

	while True:
		try:
			raw = input("Enter initial true symbols (A-Z, spaces allowed), then press Enter: ")
		except (EOFError, KeyboardInterrupt):
			print("\nInput cancelled. Keeping facts from file.")
			return None

		try:
			parsed_symbols = parse_modified_facts(raw)
			return parsed_symbols
		except ValueError as err:
			print(f"Invalid input: {err}")
			print("Please try again.")


def apply_modified_facts(parsed: ParsedData, true_symbols: set[str]) -> None:
	for char, letter in list(parsed.letters_by_char.items()):
		Letter.set(char, False, parsed, queried=letter.queried)

	for char in sorted(true_symbols):
		if char not in parsed.letters_by_char:
			Letter.create(char, parsed)
		letter = Letter.get(char, parsed)
		Letter.set(char, True, parsed, queried=letter.queried)

def main() -> None:
	parser = argparse.ArgumentParser(description="Backward-chaining expert system")
	parser.add_argument("input_file", nargs="?", default="easy.txt", help="Path to knowledge base file")
	parser.add_argument("--explain", action="store_true", help="Write detailed reasoning to explanation.txt")
	parser.add_argument("--e", action="store_true", help="Short alias for --explain")
	parser.add_argument("--modify", action="store_true", help="Interactively override initial true facts")
	parser.add_argument("--m", action="store_true", help="Short alias for --modify")
	args = parser.parse_args()

	parsed = read_file(Path(args.input_file))
	if not any(letter.queried for letter in parsed.letters_by_char.values()):
		print("Please provide at least one query in the input file (lines starting with '?').")
		return

	auto_modify = not has_initial_true_facts(parsed)
	if args.modify or args.m or auto_modify:
		modified_facts = prompt_modified_facts(
			no_facts_message=auto_modify,
		)
		if modified_facts is not None:
			apply_modified_facts(parsed, modified_facts)
			facts_label = "".join(sorted(modified_facts)) if modified_facts else "none"
			print(f"Using modified facts: {facts_label}")
	# print(json.dumps(asdict(parsed), indent=2, sort_keys=True))
	explanation_path = Path("explanation.txt") if (args.explain or args.e) else None
	solve(parsed, explanation_file=explanation_path)


if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		print(f"Invalid input file: {e}")