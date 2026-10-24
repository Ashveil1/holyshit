#!/bin/bash
cd ~/holyshit/ai/wnn
python3 -u b515.py sanity sumto
python3 -u b515.py baseline sumto
python3 -u b515.py oops even,sumto
python3 -u b515.py baseline square,choose2
python3 -u b515.py oops square,choose2
echo ALLDONE
