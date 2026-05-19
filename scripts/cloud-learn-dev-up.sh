#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${CLOUD_LEARN_HOME:-$(cd "${SCRIPT_PATH}/.." && pwd)}"
HOST_OS="$(uname -s)"

install_multipass() {
  case "$HOST_OS" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        printf '%s\n' 'Multipass is missing. Attempting to install it with Homebrew Cask...' >&2
        brew install --cask multipass
        return 0
      fi
      printf '%s\n' 'Multipass is missing and Homebrew is not available.' >&2
      printf '%s\n' 'Install it manually with: brew install --cask multipass' >&2
      return 1
      ;;
  esac
  return 1
}

ensure_multipass() {
  case "$HOST_OS" in
    Darwin)
      if command -v multipass >/dev/null 2>&1; then
        if multipass list --format json >/dev/null 2>&1; then
          return 0
        fi
        printf '%s\n' 'Multipass is installed but not ready yet. Open Multipass Desktop and wait for it to finish starting.' >&2
        return 1
      fi
      install_multipass
      if command -v multipass >/dev/null 2>&1 && multipass list --format json >/dev/null 2>&1; then
        return 0
      fi
      printf '%s\n' 'Multipass install completed but it is still not ready.' >&2
      printf '%s\n' 'Open Multipass Desktop once, wait for it to initialize, then rerun this script.' >&2
      return 1
      ;;
  esac
  return 0
}

case "$HOST_OS" in
  Darwin)
    ensure_multipass
    ;;
esac

exec bash "${ROOT_DIR}/scripts/cloud-learn" dev up --detach "$@"
