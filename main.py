import json
from dataclasses import asdict
import argparse
from pathlib import Path
from solver import solve
from parser import read_file, ParsedData

def main() -> None:
	parser = argparse.ArgumentParser(description="Backward-chaining expert system")
	parser.add_argument("input_file", nargs="?", default="easy.txt", help="Path to knowledge base file")
	args = parser.parse_args()

	parsed = read_file(Path(args.input_file))
	# print(json.dumps(asdict(parsed), indent=2, sort_keys=True))
	solve(parsed)


if __name__ == "__main__":
    main()