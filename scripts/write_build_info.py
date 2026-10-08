#!/usr/bin/env python3
"""Record a successfully published image and add the Actions job summary."""

import datetime
import json
import os
import sys
from pathlib import Path


versions = json.loads(Path(sys.argv[1]).read_text())
image = os.environ["IMAGE_NAME"]
digest = os.environ["IMAGE_DIGEST"]
run_url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
info = {
    **versions,
    "image": image,
    "digest": digest,
    "platforms": ["linux/amd64", "linux/arm64"],
    "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "source_commit": os.environ["GITHUB_SHA"],
    "workflow_run": run_url,
}
Path(sys.argv[2]).write_text(json.dumps(info, indent=2) + "\n")
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write(f"## Published `{image}:latest`\n\n")
        summary.write(f"Caddy **{versions['caddy_version']}**, AMD64 + ARM64.\n\n")
        summary.write(f"Digest: `{digest}`\n\n")
        summary.write("| Plugin | Commit |\n|---|---|\n")
        for name, plugin in versions["plugins"].items():
            summary.write(f"| {name} | [`{plugin['commit'][:12]}`](https://github.com/{plugin['repository']}/commit/{plugin['commit']}) |\n")
        summary.write(f"\n```bash\ndocker pull {image}:latest\n```\n")
