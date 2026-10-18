#!/usr/bin/env python3
"""Download MNIST and convert to the hex-text format ai/wnn/mnist.holy reads.
Data prep only - the model itself is pure holyshit (see mnist.holy).
Usage: python3 ai/wnn/prepare_mnist.py [outdir]   (writes mnist_train_raw.txt, mnist_test_raw.txt)
"""
import gzip, os, struct, sys, urllib.request

BASE = "https://storage.googleapis.com/cvdf-datasets/mnist/"
FILES = ["train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz",
         "t10k-images-idx3-ubyte.gz", "t10k-labels-idx1-ubyte.gz"]

def fetch(outdir):
    paths = []
    for f in FILES:
        p = os.path.join(outdir, f)
        if not os.path.exists(p):
            print("downloading", f)
            urllib.request.urlretrieve(BASE + f, p)
        paths.append(p)
    return paths

def load(path, magic):
    with gzip.open(path, "rb") as f:
        if magic == 2051:
            m, n, r, c = struct.unpack(">IIII", f.read(16))
            assert m == magic
            return n, r * c, f.read()
        m, n = struct.unpack(">II", f.read(8))
        assert m == magic
        return n, f.read()

def convert(imgp, labp, out):
    n, npix, imgs = load(imgp, 2051)
    nl, labs = load(labp, 2049)
    assert n == nl
    with open(out, "w") as f:
        f.write(f"{n} {npix}\n")
        for i in range(n):
            b = i * npix
            f.write(str(labs[i]) + " " + imgs[b:b + npix].hex() + "\n")
    print("wrote", out, n, "images")

if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    ti, tl, vi, vl = fetch(outdir)
    convert(ti, tl, os.path.join(outdir, "mnist_train_raw.txt"))
    convert(vi, vl, os.path.join(outdir, "mnist_test_raw.txt"))
