#!/usr/bin/env bash
# Prepare a fresh cloud container for the session tools. Idempotent.
set -euo pipefail

pip install -q jinja2 imageio-ffmpeg 2>/dev/null

# Headless Chromium must trust the agent-proxy CA (otherwise ERR_CERT_AUTHORITY_INVALID).
if ! command -v certutil >/dev/null; then
  apt-get update -q >/dev/null 2>&1 || true
  apt-get install -y -q libnss3-tools >/dev/null 2>&1
fi
mkdir -p /root/.pki/nssdb
certutil -d sql:/root/.pki/nssdb -L 2>/dev/null | grep -q ccr-agent-proxy ||
  certutil -d sql:/root/.pki/nssdb -A -t "C,," -n ccr-agent-proxy -i /root/.ccr/agent-proxy-ca.crt

echo "setup ok"
