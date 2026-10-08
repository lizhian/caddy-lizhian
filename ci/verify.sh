#!/bin/sh
set -eu

expected_version="${1:-latest}"
actual_version="$(caddy version | cut -d ' ' -f 1)"
caddy version
if [ "$expected_version" != latest ] && [ "$actual_version" != "$expected_version" ]; then
    echo "Expected Caddy $expected_version, got $actual_version" >&2
    exit 1
fi

modules="$(caddy list-modules)"
for module in http.handlers.forward_proxy layer4.handlers.socks5 dns.providers.cloudflare; do
    printf '%s\n' "$modules" | grep -Fx "$module"
done

# Provision all three plugins without starting listeners or requesting a certificate.
caddy validate --config /tmp/caddy-ci/Caddyfile --adapter caddyfile
