#!/usr/bin/env bash
# dub.sh — youtube-auto-dub 便捷封装 (py 命令后端)
# 用项目自带 .venv,绕开外部包装脚本
# 用法:
#   ./dub.sh <URL>          配音 + 中英双语字幕 (源语->中文配音)
#   ./dub.sh <URL> en       英文字幕 + 保留原声 (目标=en; 若源即en则不配音)
#   ./dub.sh <URL> cn       中文字幕 + 中文配音
# 可选第三参数: whisper 模型 (tiny/base/small/medium, 默认 small)
# 环境变量:
#   VOICE=zh-CN-YunjianNeural   换配音声音(男)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

URL="${1:?用法: ./dub.sh <YouTube-URL> [en|cn] [whisper模型]}"
VARIANT="${2:-default}"
WM="${3:-small}"
VOICE="${VOICE:-zh-CN-XiaoxiaoNeural}"

case "$VARIANT" in
  default)
    # 配音 + 中英双语字幕; 音源语言自动识别, 配音目标=中文
    ARGS=(--mode both --lang_sub zh-CN --lang_dub zh-CN --bilingual --voice "$VOICE") ;;
  en)
    # 英文字幕 + 英文配音(=保留原声, main.py 检测到源==en 自动跳过配音)
    ARGS=(--mode both --lang_sub en --lang_dub en) ;;
  cn)
    # 中文字幕 + 中文配音
    ARGS=(--mode both --lang_sub zh-CN --lang_dub zh-CN --voice "$VOICE") ;;
  *) echo "未知变体: $VARIANT (可选: 空/en/cn)" >&2; exit 2 ;;
esac

echo "▸ URL:     $URL"
echo "▸ 变体:    $VARIANT  |  Whisper: $WM"
echo

exec .venv/bin/python main.py "$URL" "${ARGS[@]}" --whisper_model "$WM"
