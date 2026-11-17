#!/usr/bin/env bash
# Set up an Ubuntu or Debian droplet to run little-helper. Safe to re-run.
#
#   LH_S3_BUCKET=<space> LH_S3_ENDPOINT=https://<region>.digitaloceanspaces.com bash deploy/bootstrap.sh
#
# Installs git, curl and tmux, then uv at the version uv.lock was written with. Builds the
# Python environment from uv.lock and writes config/local.yaml. Creates an empty,
# private GitHub token file and installs the systemd user service (it does not start it).
# Then runs the tests. It never asks for or stores a secret: the list at the end says
# which files to put them in. Guide: deploy/README.md.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$HOME/.config/little-helper"
UV_VERSION="0.12.10"
UV="$HOME/.local/bin/uv"
SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"
todo=()
step() { printf '\n== %s\n' "$*"; }

step "System packages"
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update -qq
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git curl ca-certificates tmux
else
  echo "not Debian or Ubuntu: install git, curl and tmux yourself"
fi
git --version

step "uv $UV_VERSION"
if ! [ -x "$UV" ] || ! "$UV" --version | grep -q "^uv $UV_VERSION"; then
  curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | sh
fi
"$UV" --version

step "Python environment from uv.lock"
cd "$REPO"
"$UV" sync --frozen

step "config/local.yaml"
mkdir -p "$CONF"
chmod 700 "$CONF"
if [ -f config/local.yaml ]; then
  echo "exists; left as it is"
else
  sed -e "s|@HOME@|$HOME|g" \
      -e "s|@BUCKET@|${LH_S3_BUCKET:-your-space-name}|g" \
      -e "s|@ENDPOINT@|${LH_S3_ENDPOINT:-https://nyc3.digitaloceanspaces.com}|g" \
      deploy/local.yaml.example > config/local.yaml
  if [ -z "${LH_S3_BUCKET:-}" ]; then
    sed -i 's|^s3_|# s3_|' config/local.yaml
    todo+=("set s3_bucket and s3_endpoint in $REPO/config/local.yaml and uncomment them (object storage is off until then)")
  fi
  echo "written"
fi

step "Secret files"
TOKEN="$CONF/github-token"
if [ ! -s "$TOKEN" ]; then
  install -m 600 /dev/null "$TOKEN"
  todo+=("paste a GitHub token into $TOKEN (already chmod 600)")
fi
echo "GitHub token file: $TOKEN"
if [ ! -f "$HOME/.aws/credentials" ]; then
  todo+=("put the Spaces access key in ~/.aws/credentials and chmod 600 it")
fi

step "systemd user service lh-collect@"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
sed -e "s|@REPO@|$REPO|g" -e "s|@UV@|$UV|g" deploy/lh-collect@.service > "$UNIT_DIR/lh-collect@.service"
# Linger keeps user services running after logout and starts enabled ones at boot.
$SUDO loginctl enable-linger "$(id -un)"
if systemctl --user daemon-reload 2>/dev/null; then
  echo "installed (not started)"
else
  todo+=("log in over SSH again, then run: systemctl --user daemon-reload")
fi

step "Tests"
"$UV" run --frozen pytest -q

step "lh info"
"$UV" run --frozen lh info || true

if [ ${#todo[@]} -gt 0 ]; then
  step "Still to do"
  for t in "${todo[@]}"; do echo "- $t"; done
fi
printf '\nNext: deploy/README.md, step 4 (check access, smoke test, start).\n'
