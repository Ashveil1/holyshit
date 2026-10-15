unsafe:
  struct Desc:
    U64 low
    U64 high
    U64 entries[4]

  struct Node:
    I64 val
    Node* next

  print sizeof(Desc)
  Desc* d = alloc(sizeof(Desc))
  d.low = 4660
  d.high = 255
  d.entries[0] = 11
  d.entries[3] = 22
  print d.low
  print d.entries[0] + d.entries[3]
  Desc* e = d + 1
  print e - d
  print d == null
  Node* a = alloc(sizeof(Node))
  Node* b = alloc(sizeof(Node))
  a.val = 1
  b.val = 2
  a.next = b
  print a.val + a.next.val
  a.next.val = 20
  print b.val
  print sizeof(Node)
print "ok"
