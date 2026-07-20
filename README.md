# youtube-auto-dub (V1)

自动为 YouTube 视频生成**双语字幕 + 中文配音**的本地流水线（macOS / Apple Silicon）。

给一个 YouTube 链接，本地完成：下载 → 语音识别 → 翻译 → 语音合成 → 混音 → 出片。全程走免费 / 本地方案，无需付费 API。

## 特性

- **一键出片**：`py <URL>` 端到端，无需手动分步。
- **双语**：保留原声轨 + 叠加中文配音，附字幕。
- **本地识别**：Whisper（faster-whisper）本地转写，支持 Apple Silicon。
- **免费翻译**：Google 非官方 RPC 翻译信道，多并发 + 指数退避防限流。
- **神经语音合成**：Edge-TTS 微软音色，失败自动回退 macOS 本地 `say`。
- **稳定混音**：pydub 内存级音频叠加 + FFmpeg 硬件加速渲染（`h264_videotoolbox`）。

## 环境要求

- macOS（Apple Silicon 推荐）
- Python 3.10+（已在 3.12 验证；3.9 及以下可能因 `onnxruntime` / `faster-whisper` 失败）
- FFmpeg（`brew install ffmpeg`）

## 安装

```bash
git clone https://github.com/sunusun-me/youtube-auto-dub-V1.git
cd youtube-auto-dub-V1

# 建虚拟环境并装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Apple Silicon 用户：`requirements.txt` 里的 `torch` 走 CPU 源即可（自动启用 Metal 加速），无需 CUDA 版。

## 用法

仓库自带一键入口 `./py`（clone 后即可用）：

```bash
# 一键：中文配音 + 中文字幕（源语自动识别）
./py "https://www.youtube.com/watch?v=<VIDEO_ID>"

# 变体
./py "<URL>" en            # 英文字幕 + 保留原声（源为 en 时跳过配音）
./py "<URL>" cn medium     # 第三参数指定 Whisper 模型 (tiny/base/small/medium, 默认 small)

# 换配音音色（男声）
VOICE=zh-CN-YunjianNeural ./py "<URL>"
```

> 可选：若想在任意目录用全局命令 `py` / `dub` / `python <URL>` 拉起配音，可自行在 shell 配置里加别名指向本目录的 `py`。仓库本身只依赖 `./py`，不强制此设置。


也可直接调用 `main.py` 自定义参数：

```bash
python main.py "<URL>" --mode both --lang_dub zh-CN --voice yunjian
```

常用参数：

| 参数 | 缩写 | 说明 |
|------|------|------|
| `url` | | YouTube 视频链接（必填） |
| `--mode` | `-m` | `sub`（仅字幕）/ `dub`（仅配音）/ `both`（字幕+配音） |
| `--lang` | `-l` | 目标语言（同时应用于字幕与配音） |
| `--lang_sub` | `-ls` | 覆盖字幕语言（如英文字幕 + 中文配音） |
| `--lang_dub` | `-ld` | 覆盖配音语言 |
| `--whisper_model` | `-wm` | Whisper 模型：`tiny` / `base` / `small` / `medium` |
| `--voice` | `-v` | 音色，支持别名 `yunjian`（沉稳男声）/ `xiaoxiao`（情感女声）/ `yunxi`（活泼男声），或完整名如 `zh-CN-XiaoxiaoNeural`，或系统本地音色 `Tingting` |
| `--browser` | `-b` | 从浏览器提取 Cookie：`chrome` / `edge` / `firefox` |

## 架构简介

**工作流**：

```
YouTube URL → 下载 → Whisper 识别 → 语义切片 → 翻译 → Edge-TTS 合成 → pydub 混音 → FFmpeg 渲染
```

1. **下载**（`src/youtube.py`）：yt-dlp 提取视频流与音频。
2. **识别**（`main.py`）：Whisper 本地转写，得到带时间戳的文本。
3. **切片**（`src/media.py`）：按静音间歇切分为自然语句（最大 ~10 秒）。
4. **翻译**（`src/googlev4.py`）：Google RPC 信道并发翻译 + 指数退避。
5. **合成**（`src/tts.py`）：Edge-TTS 音色映射，失败回退本地 `say`。
6. **混音**（`src/media.py`）：pydub 内存级叠加原声与配音。
7. **渲染**（`main.py`）：FFmpeg 硬件加速封装音轨 + 字幕。

**目录结构**：

```
youtube-auto-dub-V1/
├── py                  # 一键配音入口
├── main.py             # CLI 解析与流水线编排
├── requirements.txt    # 依赖快照
├── language_map.json   # 语言 → 默认音色映射
└── src/
    ├── models.py       # 核心数据结构
    ├── youtube.py      # yt-dlp 下载封装
    ├── media.py        # 切片 / 混音 / 渲染
    ├── googlev4.py     # Google RPC 翻译信道
    ├── tts.py          # Edge-TTS 合成 + 本地回退
    └── ui.py           # Rich 终端渲染
```

运行产物：`output/`（成品视频）、`.cache/`（下载缓存）、`temp/`（临时切片，单次运行后自动清空）。缓存可随时 `rm -rf .cache/*` 释放。

## 安全须知

> 本工具仅供**个人学习与技术研究**。请遵守所在地区版权法规与 YouTube / Google / Microsoft 服务条款。因不当使用（批量下载、再分发受版权保护内容、绕过平台限制）导致的账号封禁或法律纠纷，由使用者自负。

**Cookie 与凭据**

- `cookies.txt` / `.venv/` 已被 `.gitignore` 忽略，**绝不入库**。
- `cookies.txt` 仅用于本地 yt-dlp 绕过登录 / 年龄限制，须自行从浏览器导出，切勿上传至任何公开仓库或聊天工具。
- 若凭据文件意外被提交，请**立即作废相关会话**（改密码 / 注销设备）——泄露的令牌在删除文件后仍可从旧 commit 访问。
- 切勿将 GitHub PAT、登录 Cookie、`.env` 放入本仓库。

**第三方接口风险**

- 翻译默认 Google 非官方 RPC、TTS 默认 Edge-TTS，均为非公开调用方式，随时可能被限流 / 改版。正式 / 长期用途建议改用官方 API（Google Cloud Translation / Azure TTS）或本地开源方案，并做好失败降级。

## 许可

基于 [@mangodxd](https://github.com/mangodxd) 的开源项目，由 **nusun** 针对 Apple Silicon (M4) 重构优化。本衍生版本遵循 **MIT** 协议，见 [LICENSE](LICENSE)。
