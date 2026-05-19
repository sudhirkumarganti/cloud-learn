#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '%s\n' "$*"
}

have_lxd() {
  command -v lxc >/dev/null 2>&1 && lxc info >/dev/null 2>&1
}

install_with_snap() {
  if command -v snap >/dev/null 2>&1; then
    if [ "$(id -u)" -eq 0 ]; then
      snap install lxd
      lxd init --auto || true
      return 0
    fi
    if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
      sudo -n snap install lxd
      sudo -n lxd init --auto || true
      return 0
    fi
  fi
  return 1
}

install_with_apt() {
  if command -v apt-get >/dev/null 2>&1; then
    if [ "$(id -u)" -eq 0 ]; then
      apt-get update
      DEBIAN_FRONTEND=noninteractive apt-get install -y lxd lxd-client
      lxd init --auto || true
      return 0
    fi
    if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
      sudo -n apt-get update
      sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y lxd lxd-client
      sudo -n lxd init --auto || true
      return 0
    fi
  fi
  return 1
}

if have_lxd; then
  log "LXD is already available."
  exit 0
fi

if install_with_snap; then
  log "LXD installed via snap."
  exit 0
fi

if install_with_apt; then
  log "LXD installed via apt."
  exit 0
fi

log "LXD bootstrap could not complete unattended."
log "Install LXD manually using the recommended host instructions, then retry EC2 launch."
exit 3
