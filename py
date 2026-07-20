#!/usr/bin/env bash
# py = 配音一键入口 (V1). 用法: py <YouTube-URL> [en|cn] [whisper模型]
# 默认: 中文配音 + 中文字幕 (源语自动识别)
# 环境变量 VOICE 可换配音音色, 如 VOICE=zh-CN-YunjianNeural (男)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

URL="${1:?用法: py <YouTube-URL> [en|cn] [whisper模型]}"
VARIANT="${2:-cn}"
WM="${3:-small}"
VOICE="${VOICE:-zh-CN-XiaoxiaoNeural}"

case "$VARIANT" in
  cn|default)
    ARGS=(--mode both --lang_sub zh-CN --lang_dub zh-CN --voice "$VOICE") ;;
  en)
    ARGS=(--mode both --lang_sub en --lang_dub en) ;;
  *) echo "未知变体: $VARIANT (可选: cn/en)" >&2; exit 2 ;;
esac

echo "▸ [V1] URL: $URL  变体:$VARIANT  Whisper:$WM"
exec .venv/bin/python main.py "$URL" "${ARGS[@]}" --whisper_model "$WM"
