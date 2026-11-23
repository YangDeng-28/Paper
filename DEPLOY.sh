#!/usr/bin/env bash
# Run in your normal terminal, where GitHub SSH is already authenticated.
set -euo pipefail
cd -- "$(dirname -- "$0")"
atlas_python=python3
if [ -x .venv/bin/python ]; then atlas_python=.venv/bin/python; fi
"$atlas_python" -m unittest discover -s tests -v
"$atlas_python" scripts/build.py
git diff --check
git add README.md requirements.txt .gitignore .github data scripts site tests DEPLOY.sh
if ! git diff --cached --quiet; then
  if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
    echo '请先配置本仓库的提交身份：git config user.name "你的名字" 和 git config user.email "你的 GitHub 提交邮箱"'
    exit 1
  fi
  git commit -m 'Build public software engineering figure atlas'
fi
git push -u origin HEAD:main
echo '代码已推送。请在仓库 Settings > Pages 中将 Source 设为 GitHub Actions。'
echo '若首次部署失败，开启 Pages 后到 Actions 重跑失败的部署。'
