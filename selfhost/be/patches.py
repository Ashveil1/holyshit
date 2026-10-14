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
    ("_st.unpack(\"<Q\", pyrt.py_pack(\"<d\", v))[0]", "pyrt.py_f64bits(v)"),
    ("pyrt.py_get(_os.environ, \"HSPATH\", \"\")", "pyrt.py_hspath()"),
    ("pyrt.py_os_path_join(pyrt.py_os_path_dirname(pyrt.py_os_path_abspath(__file__)), \"runtime\", \"json.hs\")", "(pyrt.py_root() + \"/runtime/json.hs\")"),
    ("(bool(arms) and pyrt.py_all(arms))", "((len(arms) > 0) and pyrt.py_all(arms))"),
    ("        self.bi_stubs[pyrt.py_key([name, n])] = (\"hsBI_\" + str(bid) + \"_\" + str(n))", "        self.bi_stubs[pyrt.py_key([name, n])] = [n, (\"hsBI_\" + str(bid) + \"_\" + str(n))]"),
    ("asm.jmp(self.bi_stubs[pyrt.py_key([name, n])])", "asm.jmp(self.bi_stubs[pyrt.py_key([name, n])][1])"),
    ("""    for _f5833_0, label in pyrt.py_sorted(pyrt.py_items(self.bi_stubs), (lambda kv: kv[1])):
      name = _f5833_0[0]
      n = _f5833_0[1]
""", """    for _f5833_0, label in pyrt.py_sorted(pyrt.py_items(self.bi_stubs), (lambda kv: kv[1][1])):
      name = pyrt.py_bi_name(_f5833_0)
      n = label[0]
      label = label[1]
"""),
    ("""      try:
        path = self._find_module(dotted, from_dir, ln)
        is_shell = false""", """      is_shell = false
      path = null
      try:
        path = self._find_module(dotted, from_dir, ln)
        is_shell = false"""),
    ("(pyrt.py_get(loads, ins[\"fn\"], null) in GenIR_JSON_CALLS)", "pyrt.py_has_key(pyrt.py_get(loads, ins[\"fn\"], null), GenIR_JSON_CALLS)"),
    ("if ((pname in GenIR_JSON_CALLS) and", "if (pyrt.py_has_key(pname, GenIR_JSON_CALLS) and"),
]
