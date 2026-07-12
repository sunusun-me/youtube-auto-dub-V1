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
    原子级 TTS 生成核心：支持微软云端高级音色，自动退化至 macOS 本地 Tingting 引擎
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
            # 失败后不要报错，无缝向下进入方案 B
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
            return True
    except Exception as e:
        console.error(f"本地 TTS 引擎完全崩溃: {e}")
        
    return False

async def generate_batch_tts(segments, voice: str):
    """
    批量调度引擎：将主程序传入的 voice 变量精准分发
    """
    console.step(f"Generating text-to-speech ({voice})")
    
    # 这里设置 5 并发，既快又不会被微软封锁
    sem = asyncio.Semaphore(5)
    
    async def worker(seg):
        async with sem:
            # 确保你的段落模型里有存放音频路径的属性
            tts_path = Path(f"temp/tts_{seg.start}.mp3")
            seg.tts_audio_path = tts_path
            
            # 使用翻译好的配音文本，没有则用原文
            txt = seg.translated_text_sub if getattr(seg, 'translated_text_sub', None) else seg.source_text
            await generate_single_tts(txt, voice, tts_path)

    tasks = [worker(seg) for seg in segments]
    await asyncio.gather(*tasks)
    console.success("TTS Generation complete")