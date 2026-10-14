#!/usr/bin/env python3
"""Programming-task eval for hs. No model calls: this is the checker.

  python3 evals/run.py --reference            # validate the suite with ref/*.hs
  python3 evals/run.py --solutions DIR        # score DIR/<task id>.hs (pass@1)
  add --json for machine output, --task ID to run one task

A task passes when every case (command-line args -> exact stdout, exit 0)
matches. Missing solution file = fail. Prompts are in tasks.json."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HS = os.path.join(os.path.dirname(HERE), "hs.py")


def run_case(path, args):
    try:
        r = subprocess.run([sys.executable, HS, "run", path] + args,
                           capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    return r.stdout, r.stderr.strip().split("\n")[-1] if r.returncode else ""


def score(tasks, dirpath):
    res = []
    for t in tasks:
        path = os.path.join(dirpath, t["id"] + ".hs")
        item = {"id": t["id"], "passed": False, "cases": 0, "failed": []}
        if not os.path.exists(path):
            item["failed"].append("missing solution")
            res.append(item)
            continue
        ok = True
        for i, c in enumerate(t["cases"]):
            out, err = run_case(path, c["args"])
            item["cases"] += 1
            if out != c["out"] or err:
                ok = False
                item["failed"].append({"case": i, "args": c["args"], "want": c["out"],
                                       "got": out, "err": err})
        item["passed"] = ok
        res.append(item)
    return res


def main(argv):
    as_json = "--json" in argv
    tasks = json.load(open(os.path.join(HERE, "tasks.json")))
    if "--task" in argv:
        tid = argv[argv.index("--task") + 1]
        tasks = [t for t in tasks if t["id"] == tid]
    if "--reference" in argv:
        d = os.path.join(HERE, "ref")
    elif "--solutions" in argv:
        d = argv[argv.index("--solutions") + 1]
    else:
        print(__doc__)
        return 2
    res = score(tasks, d)
    n = sum(1 for r in res if r["passed"])
    if as_json:
        print(json.dumps({"passed": n, "total": len(res), "pass_at_1": n / max(1, len(res)),
                          "tasks": res}, indent=1))
    else:
        for r in res:
            print(("ok   " if r["passed"] else "FAIL ") + r["id"],
                  "" if r["passed"] else json.dumps(r["failed"])[:300])
        print(f"{n}/{len(res)} passed")
    return 0 if n == len(res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
