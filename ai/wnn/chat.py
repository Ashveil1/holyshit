#!/usr/bin/env python3
"""chat.py - ready-to-run interactive chat front end for hsml (see HSML.md).

No driver writing needed:
    git clone <repo> && cd holyshit/ai/wnn
    python3 chat.py --demo-world

Memory (everything you taught) lives in a local file, default ./hsml_memory.pkl.
Updating the code (git pull) never touches it: on start, saved memory is overlaid
onto a freshly derived baseline. NEVER load a memory file from someone you do not
trust - pickle loading executes code. See HSML.md.
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHEATSHEET = """Exact phrasings hsml understands (Thai, exact - other phrasings get an honest no-answer):

  Teach a procedure (by examples):
    วิธีนี้ชื่อ บวกห้า          name a new way
    ถ้า n เป็น 3 ตอบ 8         give an example (it asks for 5, then checks you)
    ตอบ 42                     answer its check question
    บวกห้า ของ 97 คืออะไร      use the taught way

  Facts about things:
    แมว มี ขน และ หาง          teach a fact
    แมว มี อะไรบ้าง            what does X have?
    แมว มี ปีก ไหม             yes/no question: answers ใช่ / ไม่ / ไม่รู้ (honest)
    แมว ไม่มี หาง              retract a fact
    ขน และ หาง                 probe: which things have these?

  help / ช่วย   this list      quit / ออก   save and exit
"""

BANNER = ("hsml chat - experimental dialog-taught system (NOT an LLM). "
          "Type 'help' for the exact phrasings, 'quit' to save & exit.")

def main():
    ap = argparse.ArgumentParser(description='Interactive chat front end for hsml')
    ap.add_argument('--memory', default='hsml_memory.pkl',
                    help='memory file path (default: ./hsml_memory.pkl)')
    ap.add_argument('--demo-world', action='store_true',
                    help='on a fresh memory, first teach the built-in Thai animal demo world')
    ap.add_argument('--seed', type=int, default=0, help='RNG seed (default: 0)')
    a = ap.parse_args()

    from hsml import HSML
    if os.path.exists(a.memory):
        try:
            h = HSML.load(a.memory, seed=a.seed)
        except Exception as e:
            # loud failure by design (B-535): never silently fall back to a fresh memory
            print(f'ERROR: could not load memory file {a.memory}: {e}', file=sys.stderr)
            sys.exit(2)
        print(f'[loaded memory: {a.memory}]')
    else:
        h = HSML(seed=a.seed)
        if a.demo_world:
            import random, b521
            n = 0
            for s in b521.gen_corpus(random.Random(0), 8):
                h.hear(s); n += 1
            print(f'[demo world taught: {n} statements]')
        print(f'[new memory - will be saved to: {a.memory}]')
    print(BANNER)

    while True:
        try:
            line = input('you> ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ('quit', 'exit', 'ออก'):
            break
        if line in ('help', 'ช่วย'):
            print(CHEATSHEET)
            continue
        r = h.hear(line)
        text = r.get('text')
        if text is None:
            text = '(ไม่มีคำตอบ - hsml has no honest answer for that)'
        print(f'hsml> {text}')
        h.save(a.memory)  # autosave every turn: taught content survives a crash

    h.save(a.memory)
    print(f'[memory saved: {a.memory}]')

if __name__ == '__main__':
    main()
