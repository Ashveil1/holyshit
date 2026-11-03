#!/usr/bin/env python3
"""run_all registration gate: the append_bytes x64 suite is registered exactly
once in run_all.SUITES and selected on both the quick and full runner paths."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_all

names = [script for script, _ in run_all.SUITES]
assert names.count("test_append_bytes_x64.py") == 1, "append_bytes suite must be registered exactly once in SUITES"
quick_selected = [script for script in names if script not in run_all.QUICK_SKIP]
assert "test_append_bytes_x64.py" in quick_selected, "append_bytes suite must run on the --quick path"
assert "test_append_bytes_x64.py" in names, "append_bytes suite must run on the full path"
assert os.path.isfile(os.path.join(HERE, "test_append_bytes_x64.py")), "registered suite file must exist on disk"
print("1/1 run_all registers test_append_bytes_x64.py exactly once; selected on quick and full paths")
