def mul(a):
  def by(x):
    return a * x
  return by

print mul(3)(4)
unsafe:
  struct Node:
    I64 val
    Node* next
    I64 tags[2]
  Node* n = alloc(sizeof(Node))
  n.val = 41
  n.tags[1] = 7
  print n.val + n.tags[1]
  Node* m = alloc(sizeof(Node))
  m.val = 100
  n.next = m
  print n.next.val
  Ptr p = alloc(16)
  *p = -5
  print *p
  print p == null
print "done"
