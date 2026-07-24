import os
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from .ui import console

# 建立一套顶级的免密钥免费语音矩阵
VOICE_MATRIX = {
    # 微软高级神经网络音色（强烈推荐，情感极度逼真）
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",     # 灵动女声（适合故事、解说）
    "xiaoyi": "zh-CN-XiaoyiNeural",         # 温柔女声
    "yunjian": "zh-CN-YunjianNeural",       # 沉稳男声（适合科技、纪录片）
    "yunxi": "zh-CN-YunxiNeural",           # 活泼男声
    "yunyang": "zh-CN-YunyangNeural",       # 新闻男声
    # 台湾腔/粤语调色盘
    "hsiao_chen": "zh-TW-HsiaoChenNeural",  # 台湾腔女声
    "hiugaai": "zh-HK-HiuGaaiNeural",       # 粤语女声
}

async def generate_single_tts(text: str, voice_name: str, output_path: Path):
    """
    原子级 TTS 生成核心：微软 Edge-TTS 优先, 失败退化 macOS say(Tingting),
    全部失败时生成 0.1s 静音兜底文件并显性告警(坏片静音优于无声消失/英文假片)
    """
    if not text.strip():
        return False
        
    # 智能解析用户输入的别名
    target_voice = VOICE_MATRIX.get(voice_name.lower(), voice_name)
    
    # 方案 A：如果使用的是微软 Edge-TTS 音色
    if "Neural" in target_voice:
        try:
            communicate = edge_tts.Communicate(text, target_voice)
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            console.warning(f"Edge-TTS [{target_voice}] 失败: {e}。自动切回 macOS 本地兜底。")
            # 注意: say 对长纯中文句语言检测不可靠(可能念成英文), 仅作降级手段
            target_voice = "Tingting"

    # 方案 B：使用 macOS 系统原生的 say 命令行引擎（包括 Tingting）
    try:
        # 先生成临时的 aiff，再通过 ffmpeg 转化为干净的 mp3
        temp_aiff = output_path.with_suffix('.aiff')
        
        # 调用 macOS 原生 say 命令
        cmd = ['say', '-v', target_voice, text, '-o', str(temp_aiff)]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.communicate()
        
        if temp_aiff.exists():
            # 转码规范化为标准 mp3
            convert_cmd = ['ffmpeg', '-y', '-i', str(temp_aiff), '-ar', '44100', '-ac', '2', str(output_path)]
            conv_proc = await asyncio.create_subprocess_exec(*convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await conv_proc.communicate()
            
            if temp_aiff.exists():
                os.remove(temp_aiff)
            if output_path.exists() and output_path.stat().st_size > 0:
                return True
    except Exception as e:
        console.error(f"本地 TTS 引擎完全崩溃: {e}")

    # 终极兜底: 生成静音片, 保证该段在时间轴上留痕且不污染混音(并显性告警)
    console.warning(f"[TTS 失败] 段落全链失败, 已用静音兜底: {text[:30]!r}...")
    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
        '-t', '0.1', str(output_path),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await proc.communicate()
    return False