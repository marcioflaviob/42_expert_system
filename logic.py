def xor(a: Letter, b: Letter) -> Truth:
    return (a.get() and not b.get()) or (not a.get() and b.get())

def and_op(a: Letter, b: Letter) -> Truth:
    return a.get() and b.get()

def or_op(a: Letter, b: Letter) -> Truth:
    return a.get() or b.get()

def not_op(a: Letter) -> Truth:
    return not a.get()