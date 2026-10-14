# ir_dump.hs: parse an IR text file with irlib.hs and print it as JSON
# (tests/test_irlib.py compares with ir.parse_module).
import irlib

print json_str(irlib.parse(read_text(argv()[0])))
