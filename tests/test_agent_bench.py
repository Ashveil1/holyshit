#!/usr/bin/env python3
"""Quick gate for the agent resource benchmark.

Runs bench_agent in quick mode (tiny synthesized scales, reference
route only) and asserts:
  - the held-out Thai/English dialogue scores 100% in every category
    (successful recall, clarification, honest miss, correction);
  - benchmark rows are produced with positive wall times and peak RSS.

The full-scale run (0/1k/10k facts, native backend, 4 GiB limit run)
is manual: python3 tests/bench_agent.py --full
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_agent


def main():
    import tempfile
    scales = [0, 50, 200]
    with tempfile.TemporaryDirectory(prefix='hs-agent-bench-test-') as td:
        tmp = Path(td)
        argv = [sys.executable, str(bench_agent.ROOT / 'interp.py'),
                str(bench_agent.REPL)]
        rows = bench_agent.bench_backend('interp', argv, tmp, scales, 30, False)
    assert len(rows) == len(scales), rows
    for r in rows:
        assert r['startup_s'] > 0 and r['startup_rss_kb'] > 0, r
        c = r['dialogue']
        for cat in bench_agent.SCORED:
            ok, total = c[cat]
            assert ok == total, (cat, ok, total)
        print('ok bench row facts=%d startup=%.2fs rss=%.1fMiB recall=%.2fms miss=%.2fms'
              % (r['facts'], r['startup_s'], r['startup_rss_kb'] / 1024,
                 r['recall_ms'], r['miss_ms']))
    n = sum(c[1] for r in rows[:1] for c in [r['dialogue'][cat] for cat in bench_agent.SCORED])
    print('ok held-out dialogue: all categories passed - %d scored replies' % n)
    print('ok agent bench quick gate (reference route)')


if __name__ == '__main__':
    main()
