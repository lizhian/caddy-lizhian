#!/usr/bin/env python3
"""Check Caddy's stable release; resolve plugin HEADs only when a build is needed."""

import argparse
import concurrent.futures
import json
import os
import re
import urllib.request
from pathlib import Path


PLUGINS = {
    "forwardproxy": "caddyserver/forwardproxy",
    "caddy_l4": "mholt/caddy-l4",
    "cloudflare": "caddy-dns/cloudflare",
}


def github_json(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "caddy-lizhian-version-checker",
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    url = os.environ.get("GITHUB_API_URL", "https://api.github.com") + path
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def latest_plugin(item):
    name, repository = item
    commits = github_json(f"/repos/{repository}/commits?per_page=1")
    sha = commits[0]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError(f"Invalid commit for {repository}: {sha}")
    return name, {"repository": repository, "commit": sha}


def resolve(previous, image, force=False):
    release = github_json("/repos/caddyserver/caddy/releases/latest")
    version = release["tag_name"]
    if release["draft"] or release["prerelease"] or not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        raise ValueError(f"Expected a stable Caddy release, got {version}")
    if force:
        reason = "forced"
    elif previous.get("image") != image or not previous.get("caddy_version"):
        reason = "first_publication"
    elif previous["caddy_version"] != version:
        reason = "caddy_version_changed"
    else:
        return {"caddy_version": version, "should_build": False, "reason": "unchanged"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        plugins = dict(pool.map(latest_plugin, PLUGINS.items()))
    return {"caddy_version": version, "should_build": True, "reason": reason, "plugins": plugins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="build-versions.json")
    parser.add_argument("--github-output")
    parser.add_argument("--previous", default="build-info.json")
    parser.add_argument("--image", default="ghcr.io/" + os.environ.get("GITHUB_REPOSITORY", "lizhian/caddy-lizhian").lower())
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    previous_file = Path(args.previous)
    previous = json.loads(previous_file.read_text()) if previous_file.exists() else {}
    versions = resolve(previous, args.image, args.force)
    if versions["should_build"]:
        Path(args.output).write_text(json.dumps({"caddy_version": versions["caddy_version"], "plugins": versions["plugins"]}, indent=2) + "\n")
    print(json.dumps(versions, indent=2))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            if versions["should_build"]:
                summary.write(f"Caddy **{versions['caddy_version']}**: build requested (`{versions['reason']}`).\n\n")
            else:
                summary.write(f"Caddy **{versions['caddy_version']}** matches the last successful publication. Docker build and plugin resolution skipped.\n\n")
    if args.github_output:
        image_version = versions["caddy_version"].removeprefix("v")
        values = {
            "caddy_version": versions["caddy_version"],
            "should_build": str(versions["should_build"]).lower(),
            "reason": versions["reason"],
            "image_version": image_version,
            "major": image_version.split(".")[0],
            "minor": ".".join(image_version.split(".")[:2]),
            **{name + "_ref": plugin["commit"] for name, plugin in versions.get("plugins", {}).items()},
        }
        with open(args.github_output, "a") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
