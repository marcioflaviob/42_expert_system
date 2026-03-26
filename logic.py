from parser import Letter, Truth

def xor(a: Letter, b: Letter) -> Truth:
    return (a.value and not b.value) or (not a.value and b.value)

def and_op(a: Letter, b: Letter) -> Truth:
    return a.value and b.value

def or_op(a: Letter, b: Letter) -> Truth:
    return a.value or b.value

def not_op(a: Letter) -> Truth:
    return not a.value