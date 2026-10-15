#!/usr/bin/env python3
"""Benchmarks: hs xbuild vs CPython on twin programs (bench/<name>.holy / .py).

    python3 bench/run.py [name ...] [--timeout SEC]

Checks that both print the same output, then reports wall time and peak RSS.
A case that exceeds --timeout (default 60 s) is reported as TIMEOUT.
"""
import os, resource, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(cmd, timeout):
    t = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, f">{timeout}s"
    return time.time() - t, p.stdout, p.stderr


def rss_mb(cmd, timeout):
    code = ("import resource,subprocess,sys;"
            "subprocess.run(sys.argv[1:],capture_output=True);"
            "print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024)")
    try:
        p = subprocess.run([sys.executable, "-c", code] + cmd,
                           capture_output=True, text=True, timeout=timeout)
        return float(p.stdout.strip())
    except Exception:
        return float("nan")


def main(argv):
    timeout = 60
    if "--timeout" in argv:
        i = argv.index("--timeout")
        timeout = int(argv[i + 1])
        del argv[i:i + 2]
    names = argv[1:] or sorted(f[:-5] for f in os.listdir(HERE) if f.endswith(".holy"))
    if not names:
        raise SystemExit("no canonical .holy benchmark sources found")
    print(f"CPython {sys.version.split()[0]}; timeout {timeout}s")
    print(f"{'case':10} {'cpython':>10} {'hs xbuild':>10} {'ratio':>8} {'MB py':>7} {'MB hs':>7}  output")
    bad = 0
    for n in names:
        exe = os.path.join(tempfile.mkdtemp(), n)
        b = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "xbuild",
                            os.path.join(HERE, n + ".holy"), "-o", exe],
                           capture_output=True, text=True)
        if b.returncode != 0:
            print(f"{n:10} xbuild FAILED: {b.stderr.strip()[:80]}")
            bad += 1
            continue
        pt, po, _ = run([sys.executable, os.path.join(HERE, n + ".py")], timeout)
        ht, ho, he = run([exe], timeout)
        if ht is None:
            print(f"{n:10} {pt:9.3f}s {'TIMEOUT':>10}  (hs {he})")
            bad += 1
            continue
        same = "same" if (po or "").split() == (ho or "").split() else "DIFFERENT"
        if same != "same":
            bad += 1
        mp = rss_mb([sys.executable, os.path.join(HERE, n + ".py")], timeout)
        mh = rss_mb([exe], timeout)
        print(f"{n:10} {pt:9.3f}s {ht:9.3f}s {pt / ht:7.2f}x {mp:7.0f} {mh:7.0f}  {same}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
