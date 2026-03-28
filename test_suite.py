from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from parser import Truth, read_file
from solver import solve, ContradictionError


@dataclass(frozen=True)
class TestCase:
    name: str
    kb: str
    expected: Dict[str, Truth]
    expect_error: Optional[type] = None


def truth_to_label(value: Truth) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return "UNDETERMINED"


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"


def colorize(text: str, code: str) -> str:
    return f"{code}{text}{Color.RESET}"


def run_case(case: TestCase) -> tuple[Optional[Dict[str, Truth]], Optional[Exception]]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        handle.write(case.kb.strip() + "\n")
        temp_path = Path(handle.name)
    try:
        parsed = read_file(temp_path)
        with redirect_stdout(io.StringIO()):
            actual = solve(parsed)
        return actual, None
    except Exception as exc:
        return None, exc
    finally:
        temp_path.unlink(missing_ok=True)


def evaluate_case(case: TestCase) -> tuple[bool, List[tuple[str, Truth, Truth]]]:
    actual, error = run_case(case)
    details: List[tuple[str, Truth, Truth]] = []

    if case.expect_error is not None:
        if error is not None and isinstance(error, case.expect_error):
            details.append(("(error)", f"{case.expect_error.__name__}", f"{type(error).__name__}"))
            return True, details
        else:
            got = type(error).__name__ if error else "no error"
            details.append(("(error)", f"{case.expect_error.__name__}", got))
            return False, details

    if error is not None:
        details.append(("(error)", "no error", type(error).__name__))
        return False, details

    passed = True
    for query in sorted(case.expected.keys()):
        expected_value = case.expected[query]
        actual_value = actual.get(query)
        details.append((query, expected_value, actual_value))
        if actual_value != expected_value:
            passed = False
    return passed, details


def print_header() -> None:
    print(colorize("Expert System Test Suite", Color.BOLD + Color.CYAN))
    print(colorize("Comparing expected vs actual query results\n", Color.CYAN))


def print_case_result(case: TestCase, passed: bool, details: List[tuple[str, Truth, Truth]]) -> None:
    title_color = Color.GREEN if passed else Color.RED
    status_text = "PASS" if passed else "FAIL"
    print(colorize(f"[{status_text}] {case.name}", Color.BOLD + title_color))
    print(f"{'Query':<12}{'Expected':<24}{'Actual':<24}{'Result':<8}")
    for query, expected, actual in details:
        if case.expect_error is not None:
            ok = passed
        else:
            ok = expected == actual
        result = "OK" if ok else "MISMATCH"
        result_color = Color.GREEN if ok else Color.RED
        expected_label = truth_to_label(expected) if isinstance(expected, (bool, type(None))) else str(expected)
        actual_label = truth_to_label(actual) if isinstance(actual, (bool, type(None))) else str(actual)
        print(
            f"{query:<12}"
            f"{expected_label:<24}"
            f"{actual_label:<24}"
            f"{colorize(result, result_color):<8}"
        )
    print()


def build_cases() -> List[TestCase]:
    return [
        TestCase(
            name="Direct implication",
            kb="""
            A => B
            =A
            ?B
            """,
            expected={"B": True},
        ),
        TestCase(
            name="Default false without support",
            kb="""
            A => B
            =A
            ?D
            """,
            expected={"D": False},
        ),
        TestCase(
            name="AND on LHS",
            kb="""
            A + B => C
            =AB
            ?C
            """,
            expected={"C": True},
        ),
        TestCase(
            name="NOT on LHS",
            kb="""
            A + !B => F
            =A
            ?F
            """,
            expected={"F": True},
        ),
        TestCase(
            name="AND on RHS sets both symbols",
            kb="""
            A => B + C
            =A
            ?BC
            """,
            expected={"B": True, "C": True},
        ),
        TestCase(
            name="Biconditional expands both directions",
            kb="""
            A <=> B
            =A
            ?B
            """,
            expected={"B": True},
        ),
        TestCase(
            name="OR in conclusion becomes undetermined when active",
            kb="""
            A => B | C
            =A
            ?BC
            """,
            expected={"B": None, "C": None},
        ),
        TestCase(
            name="OR in conclusion inactive keeps default false",
            kb="""
            A => B | C
            =
            ?BC
            """,
            expected={"B": False, "C": False},
        ),
        TestCase(
            name="XOR in conclusion becomes undetermined when active",
            kb="""
            A => B ^ C
            =A
            ?BC
            """,
            expected={"B": None, "C": None},
        ),
        TestCase(
            name="Negated conclusion sets symbol false",
            kb="""
            A => !V
            =A
            ?V
            """,
            expected={"V": False},
        ),
        TestCase(
            name="Provided easy case",
            kb="""
            A => B
            A + D => B
            =A
            ?D
            """,
            expected={"D": False},
        ),
        TestCase(
            name="Provided complex input expectations",
            kb="""
            C => E
            A + B + C => D
            A | B => C
            A + !B => F
            C | !G => H
            V ^ W => X
            A + B => Y + Z
            C | D => X | V
            E + F => !V
            A + B => C
            C => A + B
            A + B <=> !C
            =ABG
            ?GVX
            """,
            expected={},
            expect_error=ContradictionError,
        ),
        TestCase(
            name="Parentheses on LHS with grouped OR",
            kb="""
            (A + B) | (C + D) => E
            =AB
            ?E
            """,
            expected={"E": True},
        ),
        TestCase(
            name="Nested parentheses with NOT on grouped LHS",
            kb="""
            !(A + B) + C => D
            =C
            ?D
            """,
            expected={"D": True},
        ),
        TestCase(
            name="Parenthesized OR on RHS becomes undetermined",
            kb="""
            A => (B | (C + D))
            =A
            ?BCD
            """,
            expected={"B": None, "C": None, "D": None},
        ),
        TestCase(
            name="Parenthesized XOR on RHS becomes undetermined",
            kb="""
            A + B => (X ^ Y)
            =AB
            ?XY
            """,
            expected={"X": None, "Y": None},
        ),
        # --- Contradiction cases ---
        TestCase(
            name="Direct contradiction: rule proves B true and false",
            kb="""
            A => B
            A => !B
            =A
            ?B
            """,
            expected={},
            expect_error=ContradictionError,
        ),
        TestCase(
            name="Contradiction via initial fact and negating rule",
            kb="""
            A => !A
            =A
            ?A
            """,
            expected={},
            expect_error=ContradictionError,
        ),
        TestCase(
            name="Contradiction through chain",
            kb="""
            A => B
            B => C
            B => !C
            =A
            ?C
            """,
            expected={},
            expect_error=ContradictionError,
        ),
        TestCase(
            name="Contradiction: AND conjunction on both sides",
            kb="""
            A + B => C
            A + B => !C
            =AB
            ?C
            """,
            expected={},
            expect_error=ContradictionError,
        ),
        TestCase(
            name="No contradiction when contradicting rule does not fire",
            kb="""
            A => B
            C => !B
            =A
            ?B
            """,
            expected={"B": True},
        ),
    ]


def main() -> int:
    cases = build_cases()
    print_header()

    total = len(cases)
    passed_count = 0

    for case in cases:
        passed, details = evaluate_case(case)
        if passed:
            passed_count += 1
        print_case_result(case, passed, details)

    failed_count = total - passed_count
    summary_color = Color.GREEN if failed_count == 0 else Color.YELLOW
    print(colorize("Summary", Color.BOLD + Color.CYAN))
    print(f"Total:  {total}")
    print(colorize(f"Passed: {passed_count}", Color.GREEN))
    print(colorize(f"Failed: {failed_count}", Color.RED if failed_count else Color.GREEN))

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
