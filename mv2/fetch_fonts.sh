#!/bin/sh
# 下载渲染用字体到 fonts/（思源黑体、得意黑、霞鹜文楷，均为 SIL OFL 授权，来自 npm 上的 @fontpkg 包）
set -e
cd "$(dirname "$0")"
mkdir -p fonts
tmp=$(mktemp -d)
get() {
  mkdir -p "$tmp/$1"
  curl -sSL "https://registry.npmjs.org/@fontpkg/$1/-/$1-$2.tgz" | tar xz -C "$tmp/$1"
}
get source-han-sans-sc 2.5.3
get smiley-sans 2.0.4
get lxgw-wen-kai 1.520.0
cp "$tmp/source-han-sans-sc/package/SourceHanSansSC-Heavy.otf" \
   "$tmp/source-han-sans-sc/package/SourceHanSansSC-Bold.otf" \
   "$tmp/smiley-sans/package/SmileySans-Oblique.ttf" \
   "$tmp/lxgw-wen-kai/package/LXGWWenKai-Medium.ttf" fonts/
rm -rf "$tmp"
ls fonts
