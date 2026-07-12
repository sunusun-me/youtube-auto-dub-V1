#!/usr/bin/env python3
import argparse
import asyncio
import shutil
import torch
import subprocess
import os
import re
import yt_dlp
from faster_whisper import WhisperModel
from rich.table import Table

from src.ui import console
from src.models import TEMP_DIR, OUTPUT_DIR
from src.youtube import download_project
from src.media import smart_chunk, generate_srt, mix_dubbing
from src.googlev4 import GoogleTranslator
# 核心修正 1：彻底砍掉不复存在的 get_voice 导入
from src.tts import generate_single_tts as tts


def get_safe_video_title(url, default_id="fallback_audio_output") -> str:
    # 尝试提取 ID
    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else default_id
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get('title', video_id)
            
            # 清理非法字符
            clean_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)
            
            # 关键修复：强制截断，确保文件名长度远小于 255 字符
            # 截取前 50 个字符加上 video_id，防止 macOS 文件系统限制
            if len(clean_title) > 50:
                clean_title = clean_title[:50] + "_" + video_id
            
            return clean_title
            
    except Exception as e:
        # 如果获取标题失败，直接返回安全的 video_id
        return video_id


def run_ffmpeg_mux(video_path, audio_path, srt_path, output_path, hard_sub=False):
    """
    基于 M4 架构深度优化的核心混流渲染引擎 - 强力音轨重构版
    """
    if not hard_sub or not srt_path:
        cmd = ['ffmpeg', '-y', '-i', str(video_path)]
        
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            cmd.extend(['-i', str(audio_path)])
            audio_index = '1'
        else:
            audio_index = '0'
            
        if srt_path and not hard_sub:
            cmd.extend(['-i', str(srt_path)])
            
        cmd.extend(['-map', '0:v:0']) 
        cmd.extend(['-map', f'{audio_index}:a:0']) 
        
        if srt_path and not hard_sub:
            sub_index = '2' if audio_index == '1' else '1'
            cmd.extend(['-map', f'{sub_index}:s:0', '-c:s', 'mov_text'])
            
        cmd.extend(['-c:v', 'copy', '-c:a', 'aac', '-ar', '44100', '-ac', '2'])
        cmd.append(str(output_path))
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return

    # 严格处理 macOS 下 FFmpeg subtitles 滤镜的绝对路径转义
    safe_srt_path = str(srt_path).replace(":", "\\:").replace("\\", "/")
    actual_audio = audio_path if (audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0) else video_path
    
    cmd = [
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-i', str(actual_audio),
        '-vf', f"subtitles='{safe_srt_path}'",
        '-c:v', 'h264_videotoolbox', # 激活 M4 硬件加速
        '-b:v', '6000k',
        '-c:a', 'aac',
        '-ar', '44100',
        '-ac', '2',
        '-b:a', '192k',
        '-map', '0:v:0',
        '-map', '1:a:0'
    ]
    
    cmd.append(str(output_path))
    subprocess.run(cmd, capture_output=True, text=True, check=True)


async def run_pipeline(args):
    base_lang = args.lang or "en"
    final_lang_sub = args.lang_sub if args.lang_sub else base_lang
    final_lang_dub = args.lang_dub if args.lang_dub else base_lang
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_size = args.whisper_model or ("base" if device == "cpu" else "small")

    # --- UI: HEADER & MINIMAL TABLE ---
    console.header("YouTube Auto Dub")

    console.header("Configuration", center=False)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Video URL", f"[#e5e7eb]{args.url}[/#e5e7eb]")
    table.add_row("Mode", f"[#e5e7eb]{args.mode.upper()}[/#e5e7eb]")
    if args.mode in ["sub", "both"]: table.add_row("Subtitles Language", f"[#e5e7eb]{final_lang_sub.upper()}[/#e5e7eb]")
    if args.mode in ["dub", "both"]: table.add_row("Dubbing Language", f"[#e5e7eb]{final_lang_dub.upper()}[/#e5e7eb]")
    if args.mode in ["dub", "both"]: table.add_row("Gender", f"[#e5e7eb]{'Male' if args.gender == 'male' else 'Female'}[/#e5e7eb]")
    table.add_row("Whisper Model", f"[#e5e7eb]{model_size.upper()} ({device.upper()})[/#e5e7eb]")
    table.add_row("Subtitle Type", f"[#e5e7eb]{'HARD (Burned-in)' if args.hard_sub else 'SOFT (Muxed)'}[/#e5e7eb]")
    
    console.print(table)
    console.print()

    # --- UI: EXECUTION FLOW ---
    with console.status("Processing...") as status:
        
        console.info("Downloading media")
        if os.path.exists(args.url):
            console.info("Detected local file, skipping download.")
            from src.models import Project
            project = Project()
            project.video_path = args.url
            project.audio_path = args.url  # 假设音频路径即文件本身
            project.video_id = "local_cache"
        else:
            project = download_project(args.url, args.browser)

        console.info(f"Transcribing speech ({model_size})")
        model = WhisperModel(model_size, device=device, compute_type="float16" if device == "cuda" else "int8")
        segs, _ = model.transcribe(str(project.audio_path), word_timestamps=False)
        raw_segments = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segs]
        
        del model
        if device == "cuda": torch.cuda.empty_cache()
        console.success("Transcription complete")

        console.info("Analyzing silence gaps")
        project.segments = smart_chunk(raw_segments)
        texts = [seg.source_text for seg in project.segments]
        
        console.info("Connecting to translation engine")
        translator = GoogleTranslator()
        
        # 字幕翻译管线
        if args.mode in ["sub", "both"]:
            console.step(f"Translating {len(texts)} subtitle segments -> {final_lang_sub.upper()}")
            sub_texts = await translator.translate_batch(texts, target=final_lang_sub)
            for i, seg in enumerate(project.segments):
                res_sub = sub_texts[i].strip() if (i < len(sub_texts) and sub_texts[i]) else ""
                seg.translated_text_sub = res_sub if res_sub else seg.source_text

        # 配音播音稿翻译管线
        if args.mode in ["dub", "both"]:
            if args.mode == "both" and final_lang_dub == final_lang_sub:
                dub_texts = sub_texts
            else:
                console.step(f"Translating {len(texts)} dubbing scripts -> {final_lang_dub.upper()}")
                dub_texts = await translator.translate_batch(texts, target=final_lang_dub)
                
            for i, seg in enumerate(project.segments):
                res_dub = dub_texts[i].strip() if (i < len(dub_texts) and dub_texts[i]) else ""
                seg.translated_text_dub = res_dub if res_dub else seg.source_text

        await translator.close()
        console.success("Translation complete")

        # TTS 合成管线
        project.dub_audio_path = None
        if args.mode in ["dub", "both"]:
            voice = args.voice  
            console.info(f"Generating text-to-speech ({voice})")
            
            sem = asyncio.Semaphore(20)
            
            async def bounded_tts(text, voice_name, output_path):
                safe_text = str(text).strip() if text else ""
                if not safe_text:
                    import subprocess
                    subprocess.run([
                        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', 
                        '-t', '0.1', str(output_path)
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                async with sem:
                    await tts(safe_text, voice_name, output_path)

            tasks = []
            for i, seg in enumerate(project.segments):
                seg.tts_audio_path = TEMP_DIR / f"tts_{i}.mp3"
                tasks.append(bounded_tts(seg.translated_text_dub, voice, seg.tts_audio_path))

            await asyncio.gather(*tasks)
                
            project.dub_audio_path = TEMP_DIR / "final_dub.wav"
            mix_dubbing(project.audio_path, project.segments, project.dub_audio_path)
            console.success("Dubbing & mixing complete")

        project.subtitle_path = None
        if args.mode in ["sub", "both"]:
            console.info("Generating SRT subtitles")
            project.subtitle_path = TEMP_DIR / "subtitles.srt"
            generate_srt(project.segments, project.subtitle_path)
            console.success("Subtitles saved")
        
        # --- 核心改进：在此处提取人类可读的真实标题并注入文件名 ---
        console.info("Fetching authentic video title for output naming")
        human_title = get_safe_video_title(args.url, default_id=project.video_id)
        
        console.info("Rendering final video (Optimized Engine)")
        lang_info = f"L-{base_lang}"
        if args.lang_sub: lang_info += f"_S-{final_lang_sub}"
        if args.lang_dub: lang_info += f"_D-{final_lang_dub}"
        
        sub_type = "hard" if args.hard_sub else "soft"
        
        # 构筑优雅且人类可读的高级文件名结构
        output_name = f"{human_title}_{args.mode}_{sub_type}_{lang_info}.mp4"
        project.output_path = OUTPUT_DIR / output_name
        
        run_ffmpeg_mux(
            video_path=project.video_path,
            audio_path=project.dub_audio_path,
            srt_path=project.subtitle_path,
            output_path=project.output_path,
            hard_sub=args.hard_sub
        )
        console.success("Video rendered successfully")

    console.print()
    console.print(f"[bold #38bdf8]Output: {project.output_path.resolve()}[/bold #38bdf8]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Auto Sub/Dub Studio")
    parser.add_argument("url", help="YouTube video URL")
    
    parser.add_argument("--lang", "-l", help="General target language (Default: vi)")
    parser.add_argument("--lang_sub", "-ls", help="Subtitle language (Overrides --lang)")
    parser.add_argument("--lang_dub", "-ld", help="Dubbing language (Overrides --lang)")
    
    parser.add_argument("--mode", "-m", choices=["sub", "dub", "both"], default="both", help="Processing mode")
    parser.add_argument("--gender", "-g", choices=["male", "female"], default="female", help="Voice gender")
    
    parser.add_argument("--browser", "-b", help="Browser to extract cookies from (chrome, edge, firefox)")
    parser.add_argument("--whisper_model", "-wm", help="Whisper model (tiny, base, small, medium)")
    
    parser.add_argument("--hard_sub", action="store_true", help="Burn subtitles permanently into video pixels")
    parser.add_argument('--voice', type=str, default='zh-CN-XiaoxiaoNeural', 
                    help='指定配音角色。例如：zh-CN-XiaoxiaoNeural (女), zh-CN-YunjianNeural (男)')
    
    args = parser.parse_args()

    if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR, ignore_errors=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(run_pipeline(args))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"\n[red]System Error: {e}[/red]")