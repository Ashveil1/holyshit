#!/bin/bash
cd "$(dirname "$0")"
python3 -u b527.py >> logs/b527_linkc.log 2>&1
