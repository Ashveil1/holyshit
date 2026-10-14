#!/usr/bin/env python3
"""Run the unchanged kernel behavioral corpus through experimental IR lowering.
The default xkernel CLI remains on its established AST backend.
"""
import os
from pathlib import Path
import runpy
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import x64gen
original=x64gen.build_xkernel
def build_ir_kernel(prog_path,out_path):
    return original(prog_path,out_path,ir_backend=True)
x64gen.build_xkernel=build_ir_kernel
runpy.run_path(str(ROOT/'tests/test_xkernel.py'),run_name='__main__')
