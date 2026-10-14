#!/usr/bin/env python3
"""Run the unchanged behavioral corpus through the retained AST reference.
The default xkernel corpus now exercises IR lowering.
"""
import os
from pathlib import Path
import runpy
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import x64gen
original=x64gen.build_xkernel
def build_ast_kernel(prog_path,out_path):
    return original(prog_path,out_path,ir_backend=False)
x64gen.build_xkernel=build_ast_kernel
runpy.run_path(str(ROOT/'tests/test_xkernel.py'),run_name='__main__')
