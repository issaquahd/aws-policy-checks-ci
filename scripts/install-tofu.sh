#!/usr/bin/env bash
# Install a pinned OpenTofu release into BIN_DIR (used by the GitLab job).
set -eu
version="${TOFU_VERSION:-1.13.1}"
bin_dir="${BIN_DIR:-/usr/local/bin}"
case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;;
esac
curl -fsSL -o /tmp/tofu.zip \
  "https://github.com/opentofu/opentofu/releases/download/v${version}/tofu_${version}_linux_${arch}.zip"
unzip -o -q /tmp/tofu.zip tofu -d "$bin_dir"
"$bin_dir/tofu" version
