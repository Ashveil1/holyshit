#!/bin/bash
cd ~/holyshit/ai/wnn
while pgrep -f b515_run.sh > /dev/null; do sleep 60; done
python3 -u b515.py oops even,sumto
python3 -u b515.py baseline even
python3 -u b515.py baseline sumto
python3 -u b515.py baseline square,choose2
echo FOLLOWUPDONE
