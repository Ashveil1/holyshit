"""Manual fixes applied to the raw translation (be.hs) by scripts/mkbe.sh.
Each entry: (old, new). A missing `old` is an error so drift is noticed."""
PATCHES = [
    ("""    lo = layout(len(asm.state()["code"]), len(asm.state()["data"]))
    code = asm.resolve_at(lo["text_vaddr"], lo["data_vaddr"])
    start_off = asm.state()["labels"]["_start"]
    return pack(code, pyrt.py_bytes(asm.state()["data"]), start_off, lo)""",
     """    lo = elf.layout(len(asm.state()["code"]))
    code = asm.resolve_at(lo["text_vaddr"], lo["data_vaddr"])
    start_off = asm.state()["labels"]["_start"]
    return elf.pack(code, asm.state()["data"], start_off, lo)"""),
    ("    gcrt.gc_data(a)", "    gcrt.gc_data()"),
    ("""    k = pyrt.py_id(by)
    if (not (k in c)):
      order = pyrt.py_dict([[_p""",
     """    c = {}
    k = 0
    if (not (k in c)):
      order = pyrt.py_dict([[_p"""),
]
