#!/usr/bin/env python3
"""Make at most one weekly activity commit without rebuilding the image."""

import datetime
import json
import subprocess
import sys
from pathlib import Path


state = Path('.github/update-check.json')
today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()
current = subprocess.run(['git', 'show', 'origin/main:' + str(state)], text=True, capture_output=True)
if current.returncode == 0:
    previous = datetime.date.fromisoformat(json.loads(current.stdout)['checked_at'])
    if (today - previous).days < 7:
        print('Weekly activity record is current; no commit needed.')
        raise SystemExit(0)

subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
subprocess.run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], check=True)
subprocess.run(['git', 'fetch', 'origin', 'main'], check=True)
subprocess.run(['git', 'checkout', '-B', 'main', 'origin/main'], check=True)
state.write_text(json.dumps({'checked_at': today.isoformat(), 'timezone': 'Asia/Shanghai', 'caddy_version': sys.argv[1]}, indent=2) + '\n')
subprocess.run(['git', 'add', str(state)], check=True)
subprocess.run(['git', 'commit', '-m', 'chore: record weekly Caddy version check'], check=True)
subprocess.run(['git', 'push', 'origin', 'HEAD:main'], check=True)
