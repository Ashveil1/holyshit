#!/usr/bin/env python3
"""Convert the SNIPS nlu-benchmark 2017-06 custom-intent-engines split into
the text format ai/wnn/intent.holy reads.
Usage: python3 ai/wnn/prepare_snips.py <path-to-2017-06-custom-intent-engines> [outdir]
Repo: https://github.com/sonos/nlu-benchmark (download separately; CC0).
"""
import glob, json, os, sys

def main(src, outdir):
    intents = sorted(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)))
    lab = {name: i for i, name in enumerate(intents)}
    rows = {"train": [], "validate": []}
    for name in intents:
        for split in rows:
            for fp in glob.glob(os.path.join(src, name, f"{split}_{name}.json")):
                d = json.load(open(fp))
                for utt in d.get(name, []):
                    text = "".join(ch["text"].lower() for ch in utt["data"])
                    text = "".join(c if (c.isalnum() or c == " ") else " " for c in text)
                    text = " ".join(text.split())
                    if text:
                        rows[split].append((lab[name], text))
    for split, fn in (("train", "snips_train.txt"), ("validate", "snips_test.txt")):
        with open(os.path.join(outdir, fn), "w") as f:
            f.write(f"{len(rows[split])} {len(intents)}\n")
            for l, t in rows[split]:
                f.write(f"{l}|{t}\n")
        print("wrote", fn, len(rows[split]))
    print("intents:", intents)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
