# youtube-auto-dub (M4 一键初始化性能稳定版)

一个专为 macOS (Apple Silicon) 与高性能环境极致优化的自动音视频本地化流水线。你只需喂给它一个 YouTube 链接，它就能在本地完成从视频下载、语音识别、分布式翻译、神经网络语音合成（TTS）到最终高保真音轨物理熔炼的全自动闭环。

💡 **架构重大重构更新**：
此版本已彻底废除高风险的批量拼接翻译和脆弱的 FFmpeg `amix` 复杂命令行滤镜。
采用异步分布式无密钥翻译信道与 pydub 内存物理音频熔炼引擎，彻底终结了长视频（800+ 切片）对齐失败、429 频率限制以及产出静音 WAV 文件的底层硬伤。

---

## ⚡ 核心工作流 (How it works)

YouTube URL ➔ 智能下载 ➔ Whisper 语音识别 ➔ 语义切片 ➔ 分布式异步翻译 ➔ Pydub 内存物理混音 ➔ FFmpeg 硬件加速压制

````

1. **智能下载 (Download)**：基于 `yt-dlp` 高效解析并分离提取原视频的高清流与无损音频。
2. **语音识别 (Transcribe)**：本地化运行 Whisper ASR，精准捕获带有绝对时间戳的原始文本。
3. **语义切片 (Chunk)**：根据静音间歇自动切分文本，将每个语音片段严格锁定在自然呼吸句内（最大 10 秒）。
4. **分布式翻译 (Translate)**：**[深度重构]** 独创 5 并发异步原子信道调用 Google Translate RPC，内置指数退避防御机制，彻底杜绝 429 频繁限制与长文对齐崩溃。
5. **语音合成 (TTS)**：通过 Edge TTS 矩阵映射，无缝调用微软招牌高级神经网络音色。
6. **物理混音 (Mix)**：**[深度重构]** 彻底放弃不稳定的 FFmpeg 声学滤镜，转而在内存中直接对 44100Hz 双声道音频实施 pydub 物理级重叠（Overlay），确保长视频音轨绝对有声且波形精准对齐。
7. **硬件压制 (Render)**：通过 FFmpeg 调用 Apple Silicon 硬件加速器（如 `h264_videotoolbox`），快速烧录软/硬字幕并完美替换目标音轨。

---

## 🚀 快速开始 (Getting Started)

### 1. 克隆项目与依赖准备
打开终端，依次执行以下命令：

```bash
# 克隆至本地并进入目录
git clone [https://github.com/mangodxd/youtube-auto-dub.git](https://github.com/mangodxd/youtube-auto-dub.git)
cd youtube-auto-dub

# 安装系统级依赖 FFmpeg（pydub 音频熔炼与视频压制的核心底座）
# macOS (M1/M2/M3/M4)
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
````

_(Windows 用户请前往 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载并将 bin 目录配置到系统环境变量 PATH 中)_

### 2. 初始化生产力环境

Bash

```
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 一键像素级恢复生产力依赖 (含 pydub, edge-tts)
pip install -r requirements.txt
```

_(可选) 如果你需要利用本地英伟达 GPU 进行加速识别，请追加安装 CUDA 版 PyTorch：_

Bash

```
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu118](https://download.pytorch.org/whl/cu118)
```

## 🎯 最佳实践指南 (Usage)

Bash

```
# 推荐：采用微软高级神经网络男声 (云健) 启动全自动音视频“双模”本地化配音（中文字幕 + 中文配音）
python main.py "[https://youtube.com/watch?v=VIDEO_ID](https://youtube.com/watch?v=VIDEO_ID)" --mode both --lang_dub zh-CN --voice yunjian

# 采用微软招牌情感女声 (晓晓) 进行细腻配音
python main.py "[https://youtube.com/watch?v=VIDEO_ID](https://youtube.com/watch?v=VIDEO_ID)" --mode both --lang_dub zh-CN --voice xiaoxiao

# 采用阳光自然的活泼男声 (云希) 快速处理技术类视频
python main.py "[https://youtube.com/watch?v=VIDEO_ID](https://youtube.com/watch?v=VIDEO_ID)" --mode both --lang_dub zh-CN --voice yunxi

# 采用 macOS 系统原生老一代本地女声 Tingting (无需网络连接)
python main.py "[https://youtube.com/watch?v=VIDEO_ID](https://youtube.com/watch?v=VIDEO_ID)" --mode both --lang_dub zh-CN --voice Tingting

# 仅生成并烧录西班牙语软字幕（不进行配音）
python main.py "[https://youtube.com/watch?v=VIDEO_ID](https://youtube.com/watch?v=VIDEO_ID)" --mode sub --lang es

# 绕过限制：针对年龄限制或需要凭证的视频，无缝从 Chrome 浏览器提取安全 Cookies
python main.py "[https://youtube.com/watch?v=VIDEO_ID](https://youtube.com/watch?v=VIDEO_ID)" --mode both --lang_dub zh-CN --voice yunxi --browser chrome
```

## 🎛️ 参数全景图 (All Options)

|**参数 (Flag)**|**缩写 (Short)**|**功能描述 (Description)**|
|---|---|---|
|`url`||YouTube 视频链接 **(必填)**|
|`--mode`|`-m`|运行模式：`sub` (仅字幕), `dub` (仅配音), 或 `both` (字幕+配音)|
|`--lang`|`-l`|目标语言（同时应用于字幕与配音）|
|`--lang_sub`|`-ls`|覆盖字幕语言（例如实现英文字幕+中文配音）|
|`--lang_dub`|`-ld`|覆盖配音语言（当与字幕语言不同时使用）|
|`--whisper_model`|`-wm`|Whisper 模型等级：`tiny`, `base`, `small`, `medium` (默认根据硬件自动降级选择)|
|`--browser`|`-b`|认证 Cookie 提取源：`chrome`, `edge`, `firefox`|
|`--gender`|`-g`|_[Legacy]_ 传统性别选择（已由 `--voice` 完美替代，不推荐使用）|
|`--voice`|`-v`|**[NEW]** 指定核心音色：`yunjian` (沉稳男声), `xiaoxiao` (情感女声), `yunxi` (活泼男声), 或系统本地音色如 `Tingting`|

## 📂 项目模块地图 (Project Structure)

Plaintext

```
youtube-auto-dub/
├── main.py                 # 调度中枢：CLI 解析与流水线生命周期编排
├── requirements.txt        # 生产力环境固化快照
├── language_map.json       # 语言与默认音色映射后备矩阵
├── src/
│   ├── models.py           # 核心数据结构 (SubtitleSegment, ProjectContext)
│   ├── youtube.py          # yt-dlp 安全封装器，负责无损流提取
│   ├── media.py            # [重构核心] 智能语义切片、Pydub 内存混音、FFmpeg 硬件级渲染压制
│   ├── googlev4.py         # [重构核心] 高并发分布式无密钥 RPC 翻译信道
│   ├── tts.py              # [重构核心] Edge-TTS 别名矩阵映射器与本地音频回滚机制
│   └── ui.py               # 基于 Rich 的精美终端渲染与故障诊断日志
├── .cache/                 # 视频流缓存池 (持久化保存，避免重复下载)
├── temp/                   # 内存/物理临时切片交换区 (单次运行后自动清空)
└── output/                 # 最终高保真成品视频输出目录
```

## 🛠️ 常见故障自检 (Troubleshooting)

- **提示找不到 FFmpeg？**
    
    - 请确保 `ffmpeg -version` 在终端能正常输出。macOS 用户请检查 `brew` 路径是否正确注入到环境变量中。
        
- **显存溢出 (CUDA Out of Memory)？**
    
    - 本地显存不足。请使用 `--whisper_model base` 或 `tiny` 降低模型体量。
        
- **遭遇 YouTube 频繁限流或需要人机验证？**
    
    - 请在运行命令前彻底关闭对应的浏览器（如 Chrome），然后追加 `--browser chrome`。若仍失效，请通过浏览器插件导出标准的 `cookies.txt`，并在 `src/youtube.py` 中挂载。
        
- **合成出来的音频没有声音或文件体积过小？**
    
    - 通常是由于选用了目标国家/地区不支持的冷门音色。请首选推荐的 `yunjian` 或 `xiaoxiao`。
        

## 🗺️ 路线图 (What we're working on)

- [ ] **声纹识别 (Speaker Diarization)** — 整合 `pyannote.audio` 自动分离多发言人，并智能匹配不同的音色。
    
- [ ] **原音分离 (BGM Separation)** — 引入 `Demucs` 物理引擎，完美保留视频原背景音乐与特效声，仅剥离并替换人声音轨。
    
- [ ] **声音克隆 (RVC)** — 允许通过少量样本克隆原作者的音色进行本地化配音。
    
- [ ] **本地大模型翻译** — 支持 `Llama 3` / `Mistral` 等本地私有化 LLM 翻译，彻底断绝网络依赖。
    

## ⚖️ 开源协议

基于 Nguyen Cong Thuan Huy (`@mangodxd`) 的优秀开源项目。

由 **nusun** 基于 M4 芯片及生产力稳定性要求进行深度重构优化。

本衍生版本遵循 **MIT** 开源协议。