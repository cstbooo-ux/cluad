#!/usr/bin/env bash
# 下载构建所需的地图数据、字体和离线语音模型（都不进仓库）
set -euo pipefail
W="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$W/data" "$W/fonts" "$W/build/models"
TMP="$(mktemp -d)"

# ---- 地图：Natural Earth（公有领域）
cd "$W/data"
for z in 50m_physical/ne_50m_land 10m_physical/ne_10m_land 50m_physical/ne_50m_lakes; do
  n=$(basename $z)
  curl -sSL -o $n.zip https://naturalearth.s3.amazonaws.com/$z.zip && unzip -oq $n.zip -d $n && rm $n.zip
done

# ---- 历史国界：aourednik/historical-basemaps（GPL-3.0）
git clone -q --depth 1 --filter=blob:none --no-checkout https://github.com/aourednik/historical-basemaps "$TMP/hb"
git -C "$TMP/hb" sparse-checkout set --no-cone /geojson/world_1938.geojson /geojson/world_1945.geojson
git -C "$TMP/hb" checkout -q
cp "$TMP/hb/geojson/world_1938.geojson" "$TMP/hb/geojson/world_1945.geojson" "$W/data/"

# ---- 字体：思源黑体/宋体（OFL）、Oswald / Roboto Condensed / IBM Plex Mono / Special Elite
git clone -q --depth 1 --filter=blob:none --no-checkout https://github.com/notofonts/noto-cjk "$TMP/cjk"
git -C "$TMP/cjk" sparse-checkout set --no-cone \
  /Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf /Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf \
  /Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Black.otf /Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-Bold.otf \
  /Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-Black.otf
git -C "$TMP/cjk" checkout -q
cp "$TMP"/cjk/*/OTF/SimplifiedChinese/*.otf "$W/fonts/"
git clone -q --depth 1 --filter=blob:none --no-checkout https://github.com/google/fonts "$TMP/gf"
git -C "$TMP/gf" sparse-checkout set --no-cone /ofl/oswald/ /ofl/robotocondensed/ /apache/specialelite/ \
  /ofl/ibmplexmono/IBMPlexMono-Medium.ttf /ofl/ibmplexmono/IBMPlexMono-SemiBold.ttf /ofl/bebasneue/
git -C "$TMP/gf" checkout -q
cp "$TMP/gf/ofl/oswald/Oswald[wght].ttf" "$W/fonts/Oswald.ttf"
cp "$TMP/gf/ofl/robotocondensed/RobotoCondensed[wght].ttf" "$W/fonts/RobotoCondensed.ttf"
cp "$TMP/gf/apache/specialelite/SpecialElite-Regular.ttf" "$W/fonts/SpecialElite.ttf"
cp "$TMP"/gf/ofl/ibmplexmono/*.ttf "$TMP/gf/ofl/bebasneue/BebasNeue-Regular.ttf" "$W/fonts/"

# ---- 离线配音模型（仅在需要重新生成 assets/tts 时使用）
if [ "${WITH_TTS_MODELS:-0}" = 1 ]; then
  cd "$W/build/models"
  for n in kokoro-multi-lang-v1_0 vits-piper-de_DE-thorsten-high vits-piper-ru_RU-denis-medium \
           vits-piper-pl_PL-darkman-medium vits-piper-fr_FR-upmc-medium; do
    curl -sSL -o $n.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/$n.tar.bz2
    tar xjf $n.tar.bz2 && rm $n.tar.bz2
  done
fi
rm -rf "$TMP"
echo "data ready"
