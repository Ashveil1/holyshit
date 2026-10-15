import kprim
DATA = 0x1F0
ERR = 0x1F1
SEC_CNT = 0x1F2
LBA0 = 0x1F3
LBA1 = 0x1F4
LBA2 = 0x1F5
DRIVE = 0x1F6
STATUS = 0x1F7
CMD_IDENTIFY = 0xEC
CMD_READ = 0x20
CMD_WRITE = 0x30
ST_ERR = 0x01
ST_DRDY = 0x40
ST_BSY = 0x80
SECTOR = 512
SPIN = 400000
def status():
  return ioport_in(STATUS, 1)
def select(lba28):
  ioport_out(DRIVE, 0xE0 | (lba28 & 0x0F), 1)
def spin():
  i = 0
  while i < SPIN:
    s = status()
    if s & ST_BSY == 0:
      return s
    i = i + 1
  return 0xFF
def wait_ready():
  s = spin()
  if s == 0xFF:
    return false
  if s & ST_ERR != 0:
    return false
  if s & ST_DRDY == 0:
    return false
  return true
def lba_setup(lba, count):
  ioport_out(SEC_CNT, count, 1)
  ioport_out(LBA0, lba & 0xFF, 1)
  ioport_out(LBA1, lba >> 8 & 0xFF, 1)
  ioport_out(LBA2, lba >> 16 & 0xFF, 1)
def identify_buf():
  return alloc(512)
def present():
  select(0)
  ioport_out(SEC_CNT, 0, 1)
  ioport_out(LBA1, 0, 1)
  ioport_out(LBA2, 0, 1)
  ioport_out(STATUS, CMD_IDENTIFY, 1)
  s = spin()
  if s == 0xFF:
    return false
  return s & ST_ERR == 0
def read_identify(buf):
  i = 0
  while i < 512:
    w = ioport_in(DATA, 2)
    unsafe:
      Ptr p = as_ptr(buf)
      store8(p + i, w & 0xFF)
      store8(p + i + 1, w >> 8 & 0xFF)
    i = i + 2
  return true
def ident_word(buf, n):
  unsafe:
    Ptr p = as_ptr(buf)
    return load8(p + n * 2) | (load8(p + n * 2 + 1) << 8)
def sectors(buf):
  return ident_word(buf, 60) | (ident_word(buf, 61) << 16)
def sectors_per_irq(buf):
  return ident_word(buf, 54) | (ident_word(buf, 55) << 16)
def model_byte(buf, i):
  unsafe:
    Ptr p = as_ptr(buf)
    return load8(p + 54 + i * 2 + 1)
def put_byte(dst, i, b):
  unsafe:
    Ptr o = as_ptr(dst)
    store8(o + i, b)
def model(buf):
  dst = alloc(48)
  n = 0
  i = 0
  while i < 20:
    b = model_byte(buf, i)
    if b != 0:
      put_byte(dst, n, b)
      n = n + 1
    i = i + 1
  s = read_mem(as_int(dst), 40)
  m = len(s)
  while m > n:
    m = m - 1
  return s[0:n]
def read(lba, count, dst):
  if count < 1 or count > 256:
    raise "ata read wants 1..256 sectors"
  select(lba >> 24)
  lba_setup(lba, count)
  ioport_out(STATUS, CMD_READ, 1)
  if not wait_ready():
    raise "ata read failed"
  unsafe:
    Ptr q = as_ptr(dst)
  i = 0
  n = count * SECTOR
  while i < n:
    w = ioport_in(DATA, 2)
    unsafe:
      store8(q + i, w & 0xFF)
      store8(q + i + 1, w >> 8 & 0xFF)
    i = i + 2
  return true
def rd8(addr, off):
  unsafe:
    Ptr p = as_ptr(addr)
    return load8(p + off)
def write(lba, count, src):
  if count < 1 or count > 256:
    raise "ata write wants 1..256 sectors"
  select(lba >> 24)
  lba_setup(lba, count)
  ioport_out(STATUS, CMD_WRITE, 1)
  if not wait_ready():
    raise "ata write failed"
  i = 0
  n = count * SECTOR
  while i < n:
    lo = rd8(src, i)
    hi = rd8(src, i + 1)
    ioport_out(DATA, lo | (hi << 8), 2)
    i = i + 2
  # the drive is busy committing the sector: the next command is ignored
  # while BSY is set, so wait for it to finish
  if not wait_ready():
    raise "ata write did not complete"
  return true
