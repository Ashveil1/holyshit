# Source -> canonical optimized IR, without Python parser/lowering.
import normalize
import irbuild
import iropt
m = irbuild.build_module(normalize.parse(read_text(argv()[0])), "")
iropt.optimize_module(m)
print json_str(m)
