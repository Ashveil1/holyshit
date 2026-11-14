def f():
    raise "boom"
def g():
    try:
        f()
    except Exception as e:
        raise
