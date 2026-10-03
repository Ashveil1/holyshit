# tour 08: unsafe — ชนิดคงที่, struct, pointer ตรง
# รัน: python3 interp.py examples/08_unsafe.hs
#
# ใน unsafe: ชนิดคงที่ (I64/U64/Ptr + struct pointer) ทุกช่อง 8 bytes
# ไม่มี padding, ไม่มี def/for/try/Str/List, และ / ตัดทศนิยมแบบ C

unsafe:
  struct Point:
    I64 x
    I64 y

  struct Desc:
    I64 kind
    Point* origin
    I64 entries[4]

  # ประกาศแบบมีชนิดเสมอ: I64/U64/Ptr หรือชื่อ struct ตามด้วย *
  Point* p = alloc(sizeof(Point) * 2)
  p.x = 3
  p.y = 4
  print p.x + p.y

  # เลื่อน pointer ได้ (หน่วยคือ sizeof ของชนิดปลายทาง = 16) และลบกันได้
  Point* q = p + 1
  q.x = 10
  q.y = 20
  print q.x, q.y, q - p

  # array field ใน struct
  Desc* d = alloc(sizeof(Desc))
  d.kind = 2
  d.entries[0] = 11
  d.entries[3] = 22
  print d.kind, d.entries[0] + d.entries[3]
  print sizeof(Desc), sizeof(Point)

  # struct pointer ซ้อน struct pointer ได้
  d.origin = p
  print d.origin.x

  # ตัวดำเนินการของภาษาใน unsafe ได้
  print 7 / 2
  print 7 % 2
  print 1 and 2
  print 0 or 5
  print not 0

  # raw bytes
  Ptr buf = alloc(8)
  store32(buf, 65530)
  print load32(buf)
  print load8(buf)

  # ค่า dynamic ข้ามเข้า unsafe ได้ด้วย as_int (และกลับด้วย as_ptr)
  print as_int(as_ptr(p))
