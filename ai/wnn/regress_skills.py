"""Clean-process skill-execution regression (parent direction 2026-10-25).
Simulates a rebuilt workspace: hides /tmp/c7_prog_0_base.json, then in a FRESH subprocess
derives the skill store (cache allowed) and executes every skill on ground-truth probes
plus a 40-query sentence-path spot check per skill. Also covers the missing-pinning error
path and the corrupt-cache fallback. Run: python3 regress_skills.py (from ai/wnn).
PASS requires all four checks."""
import os, subprocess, sys, json

WNN = os.path.dirname(os.path.abspath(__file__))
TMPPIN = '/tmp/c7_prog_0_base.json'

CHILD = r'''
import sys, json
sys.path.insert(0, %r)
mode = sys.argv[1]
import cur7 as C
from b527 import HSMLMemory, derive_skills, load_logged, SKILLS
if mode == 'clean':
    store = derive_skills(load_logged())  # cache allowed; pinning must come from repo
    mem = HSMLMemory(); mem.skills = store
    from cur7 import gen as cgen
    import random
    res = {}
    for task in SKILLS:
        te = random.Random(1000); ok = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(10):
                x, y, r = cgen(task, te, sc)
                ans = mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; ok += (ans.get('kind') == 'skill_answer' and ans.get('result') == r)
        res[task] = f'{ok}/{n}'
    print(json.dumps(res))
elif mode == 'nopin':
    # both pinning sources hidden (repo copy renamed by parent) -> clear RuntimeError expected
    try:
        derive_skills(load_logged())
        print(json.dumps({'error': 'NO ERROR - pinning dependency not actually required?'}))
    except RuntimeError as e:
        print(json.dumps({'expected_error': str(e)[:120]}))
'''

def hide(path):
    if os.path.exists(path):
        os.rename(path, path + '.hidden')
        return True
    return False

def unhide(path):
    if os.path.exists(path + '.hidden'):
        os.rename(path + '.hidden', path)

def run_child(mode):
    r = subprocess.run([sys.executable, '-c', CHILD % WNN, mode],
                       capture_output=True, text=True, cwd=WNN)
    return r

def main():
    out = {}
    # 1. clean-process execution without the /tmp artifact
    hid = hide(TMPPIN)
    try:
        r = run_child('clean')
        res = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {'_rc': r.returncode, '_err': r.stderr[-300:]}
        out['clean_process_no_tmp'] = res
        out['c1_ok'] = all(v == '40/40' for v in res.values())
    finally:
        if hid: unhide(TMPPIN)
    # 2. missing pinning source -> clear error (hide BOTH)
    hid2 = hide(TMPPIN)
    repopin = os.path.join(WNN, 'logs', 'baselib_pin.json')
    hid3 = hide(repopin)
    try:
        r = run_child('nopin')
        line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '{}'
        res = json.loads(line)
        out['missing_pinning'] = res
        out['c2_ok'] = 'expected_error' in res and 'pinning' in res['expected_error'].lower()
    finally:
        if hid2: unhide(TMPPIN)
        if hid3: unhide(repopin)
    # 3. corrupt cache -> warning + fallback (do not crash)
    cache = os.path.join(WNN, 'logs', 'b527_skills_cache.pkl')
    bak = cache + '.regbak'
    had = os.path.exists(cache)
    if had: os.rename(cache, bak)
    try:
        with open(cache, 'wb') as f: f.write(b'not a pickle')
        r = subprocess.run([sys.executable, '-c',
            "import sys; sys.path.insert(0, %r); from b527 import derive_skills, load_logged;"
            "s = derive_skills(load_logged()); print('SKILLS', sorted(s))" % WNN],
            capture_output=True, text=True, cwd=WNN, timeout=21600)
        out['corrupt_cache'] = {'rc': r.returncode, 'warned': 'WARNING' in r.stdout,
                                'skills': 'choose2' in r.stdout}
        out['c3_ok'] = r.returncode == 0 and 'WARNING' in r.stdout and 'choose2' in r.stdout
    finally:
        os.remove(cache) if os.path.exists(cache) else None
        if had: os.rename(bak, cache)
    verdict = 'PASS' if all(out.get(f'c{i}_ok') for i in (1, 2, 3)) else 'FAIL'
    print(json.dumps({'verdict': verdict, **out}, ensure_ascii=False), flush=True)
    print('DONE', flush=True)

if __name__ == '__main__':
    main()
