#!/usr/bin/env bash
# Create the public GitHub repo and push main.
# Requires: gh auth login
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI 未登录。先运行: gh auth login" >&2
  exit 1
fi
login="$(gh api user --jq .login)"
if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create rime-gloss --public --source=. --remote=origin --description "Rime universal gloss pack: EN/JA short glosses beside Chinese candidates"
fi
git push -u origin main
echo "安装命令:"
echo "  bash rime-install ${login}/rime-gloss"
