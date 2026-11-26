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

assert names.count("test_std_path.py") == 1
assert "test_std_path.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_std_path.py"))
print("1/1 run_all registers std.path exactly once on quick and full paths")

assert names.count("test_std_str.py") == 1
assert "test_std_str.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_std_str.py"))
print("1/1 run_all registers std.str helpers exactly once on quick and full paths")

assert names.count("test_std_fmt.py") == 1
assert "test_std_fmt.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_std_fmt.py"))
print("1/1 run_all registers std.fmt formatting exactly once on quick and full paths")

assert names.count("test_std_list.py") == 1
assert "test_std_list.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_std_list.py"))
print("1/1 run_all registers std.list helpers exactly once on quick and full paths")

assert names.count("test_agent_fetch.py") == 1
assert "test_agent_fetch.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_agent_fetch.py"))
print("1/1 run_all registers agent fetch semantics exactly once on quick and full paths")

assert names.count("test_agent_fetch_timeouts.py") == 1
assert "test_agent_fetch_timeouts.py" in names
assert "test_agent_fetch_timeouts.py" not in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_agent_fetch_timeouts.py"))
print("1/1 run_all registers agent fetch bounded transport exactly once on the full path (quick-skipped)")

assert names.count("test_json_str_routes.py") == 1
assert "test_json_str_routes.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_json_str_routes.py"))
print("1/1 run_all registers json_str 7-route parity exactly once on quick and full paths")

assert names.count("test_shell_disk.py") == 1
assert "test_shell_disk.py" in names, "shell-disk suite must run on the full path"
assert "test_shell_disk.py" in run_all.QUICK_SKIP, "shell-disk boots QEMU; pinned to the full path like test_shell_boot"
assert os.path.isfile(os.path.join(HERE, "test_shell_disk.py"))
print("1/1 run_all registers shell-disk exactly once on the full path, quick-skipped with the other QEMU suites")

assert names.count("test_agent_lineage_fetch.py") == 1
assert "test_agent_lineage_fetch.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_agent_lineage_fetch.py"))
print("1/1 run_all registers agent lineage-fetch exactly once on quick and full paths")

assert names.count("test_agent_corpus_benchmark.py") == 1
assert "test_agent_corpus_benchmark.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_agent_corpus_benchmark.py"))
print("1/1 run_all registers the A19.1 benchmark gate exactly once on quick and full paths")

assert names.count("test_agent_corpus_preprocess.py") == 1
assert "test_agent_corpus_preprocess.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_agent_corpus_preprocess.py"))
print("1/1 run_all registers the A19.1 preprocessing gate exactly once on quick and full paths")

assert names.count("test_agent_corpus_driver.py") == 1
assert "test_agent_corpus_driver.py" in quick_selected
assert os.path.isfile(os.path.join(HERE, "test_agent_corpus_driver.py"))
print("1/1 run_all registers the A19.1 driver gate exactly once on quick and full paths")
assert names.count("test_shell_edit.py") == 1
assert "test_shell_edit.py" in names, "shell-edit suite must run on the full path"
assert "test_shell_edit.py" in run_all.QUICK_SKIP, "shell-edit boots QEMU; pinned to the full path like test_shell_boot"
assert os.path.isfile(os.path.join(HERE, "test_shell_edit.py"))
print("1/1 run_all registers shell-edit exactly once on the full path, quick-skipped with the other QEMU suites")
