I64 fib(I64 n) {
  if (n < 2) {
    return n;
  }
  return fib(n-1) + fib(n-2);
}
Print(fib(10));
Print(fib(15));
