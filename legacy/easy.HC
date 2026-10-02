# no types, no semicolons
x = 2 + 3 * 4
Print x
Print "hello"

for i in 0..5 {
  Print i
}

I64 fib(I64 n) {
  if (n < 2) {
    return n
  }
  return fib(n-1) + fib(n-2)
}
Print "fib:", fib(10)
