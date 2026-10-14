# Canonical AST JSON -> unoptimized IR JSON (test interchange).
import irbuild
prog = json_load(argv()[0])
m = irbuild.build_module(prog, "")
print json_str(m)
