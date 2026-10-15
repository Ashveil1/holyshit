# Canonical AST JSON -> unoptimized IR JSON (test interchange).
import irbuild
prog = json_load(argv()[0])
builder = irbuild.Builder("")
m = builder.build(prog, "")
print json_str(m)
