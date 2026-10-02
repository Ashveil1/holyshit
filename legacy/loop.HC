I64 i = 0;
I64 s = 0;
while (i < 10) {
  s = s + i;
  i = i + 1;
}
Print(s);
if (s == 45) {
  Print(1);
} else {
  Print(0);
}
