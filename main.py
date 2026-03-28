import json
from dataclasses import asdict
import argparse
from pathlib import Path
from solver import solve
from parser import read_file, ParsedData

def main() -> None:
	parser = argparse.ArgumentParser(description="Backward-chaining expert system")
	parser.add_argument("input_file", nargs="?", default="easy.txt", help="Path to knowledge base file")
	parser.add_argument("--explain", action="store_true", help="Write detailed reasoning to explanation.txt")
	parser.add_argument("--e", action="store_true", help="Short alias for --explain")
	args = parser.parse_args()

	parsed = read_file(Path(args.input_file))
	# print(json.dumps(asdict(parsed), indent=2, sort_keys=True))
	explanation_path = Path("explanation.txt") if (args.explain or args.e) else None
	solve(parsed, explanation_file=explanation_path)


if __name__ == "__main__":
    main()