import os
import subprocess
from pathlib import Path
from typing import List
from pydub import AudioSegment
from .models import SubtitleSegment
from .ui import console

def smart_chunk(raw_segments: List[dict]) -> List[SubtitleSegment]:
    """
    智能文本切片聚合引擎 - 优化长文本边界对齐
    """
    if not raw_segments: 
        return []
    chunks, curr_chunk = [], [raw_segments[0]]
    
    for curr in raw_segments[1:]:
        prev = curr_chunk[-1]
        gap = curr['start'] - prev['end']
        duration = curr['end'] - curr_chunk[0]['start']
        
        # 0.8秒静音间隙或单句超过10秒，强制切分，保证配音语速自然
        if gap > 0.8 or duration > 10.0:
            chunks.append(SubtitleSegment(
                start=curr_chunk[0]['start'], 
                end=curr_chunk[-1]['end'],
                source_text=" ".join(s['text'] for s in curr_chunk).strip()
            ))
            curr_chunk = [curr]
        else:
            curr_chunk.append(curr)

    if curr_chunk:
        chunks.append(SubtitleSegment(
            start=curr_chunk[0]['start'], 
            end=curr_chunk[-1]['end'],
            source_text=" ".join(s['text'] for s in curr_chunk).strip()
        ))
    console.step(f"Grouped into {len(chunks)} segments")
    return chunks


def generate_srt(segments: List[SubtitleSegment], output_path: Path):
    """
    SRT 字幕生成引擎 - 带有精准时间戳和翻译文本防御保护
    """
    def fmt_time(seconds: float) -> str:
        h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            # 优先使用翻译好的字幕，如果为空则使用原文字幕保底
            text = seg.translated_text_sub if getattr(seg, 'translated_text_sub', None) else seg.source_text
            f.write(f"{i}\n{fmt_time(seg.start)} --> {fmt_time(seg.end)}\n{text}\n\n")


def mix_dubbing(og_audio: Path, segments: List[SubtitleSegment], output_path: Path):
    """
    基于 M4 架构极致优化的分布式内存混音引擎 - 彻底终结 800+ 切片的静音恶梦
    """
    console.step("Mixing dubbing with original audio...")
    
    # 筛选出有声且文件真实存在的有效 TTS 配音切片
    valid_clips = [seg for seg in segments if getattr(seg, 'tts_audio_path', None) and Path(seg.tts_audio_path).exists()]
    
    try:
        # 1. 载入原视频音轨作为声场基底
        if og_audio.exists() and og_audio.stat().st_size > 0:
            final_mix = AudioSegment.from_file(str(og_audio))
        else:
            # 防御降级：如果原音轨缺失，依据最后一个切片自动合成静音轨垫底
            total_duration_ms = int(segments[-1].end * 1000) + 5000 if segments else 10000
            final_mix = AudioSegment.silent(duration=total_duration_ms, frame_rate=44100)
        
        # 2. 强制规范化原音基底（统一为 44100Hz, 双声道），消除底层采样率冲突引起的失真
        final_mix = final_mix.set_frame_rate(44100).set_channels(2)
        
        # 将原视频背景音优雅压低 12 分贝，给配音婷婷留出清晰的声场空间
        final_mix = final_mix - 12
        
        if not valid_clips:
            console.warning("No valid TTS audio clips found. Exporting faded original audio.")
            final_mix.export(str(output_path), format="wav")
            return

        # 3. 内存物理拓扑：按时间戳物理重叠（Overlay）每个音频切片
        success_count = 0
        for seg in valid_clips:
            try:
                tts_segment = AudioSegment.from_file(str(seg.tts_audio_path))
                # 强制将 TTS 切片提升至相同的音频规格
                tts_segment = tts_segment.set_frame_rate(44100).set_channels(2)
                
                # 计算毫秒级时间轴位置
                start_ms = max(0, int(seg.start * 1000))
                
                # 物理重叠融入主音轨中
                final_mix = final_mix.overlay(tts_segment, position=start_ms)
                success_count += 1
            except Exception:
                continue
                
        console.info(f" -> 物理音频编排完成，成功熔炼 {success_count}/{len(segments)} 个配音切片...")
        
        # 4. 导出为高品质无损 WAV 容器文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_mix.export(str(output_path), format="wav")
        console.success(f" -> [混音成功] 目标音轨体积: {output_path.stat().st_size // 1024} KB")
        
    except Exception as e:
        console.error(f"混音核心引擎遭遇未知异常: {e}。启动降级保底。")
        # 终极防御：即使内存混音崩溃，也绝不生成 0KB 损坏文件，直接拷贝原音频防止后续渲染卡死
        if og_audio.exists():
            import shutil
            shutil.copy(str(og_audio), str(output_path))


def render_video(video_path: Path, subtitle_path: Path | None, dub_audio_path: Path | None, output_path: Path):
    """
    原生高性能渲染引擎 - 强力击穿一切多音轨冲突
    """
    console.step("Rendering video...")
    
    # 建立底层命令，分离音视频逻辑
    cmd = ['ffmpeg', '-y', '-i', str(video_path)]
    
    has_dub = dub_audio_path and dub_audio_path.exists() and dub_audio_path.stat().st_size > 0
    if has_dub:
        cmd.extend(['-i', str(dub_audio_path)])
        
    if subtitle_path and subtitle_path.exists():
        # 安全处理 macOS 下 FFmpeg subtitles 滤镜的路径转义灾难
        sub_path_str = str(subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
        cmd.extend(['-vf', f"subtitles='{sub_path_str}'"])
        
    # 精准物理映射流：彻底切断原视频自带的干扰音轨
    cmd.extend(['-map', '0:v:0']) # 锁定原视频画面
    
    if has_dub:
        cmd.extend(['-map', '1:a:0']) # 锁定新合成的配音音轨
        # 使用现代播放器通用的高规格双声道 AAC 重编码，确保 Mac/iPhone 绝对不会静音
        cmd.extend(['-c:v', 'libx264', '-c:a', 'aac', '-b:a', '256k', '-ar', '44100', '-ac', '2'])
    else:
        cmd.extend(['-map', '0:a:0?']) # 如果没配音，尝试保留原视频声音
        cmd.extend(['-c:v', 'libx264', '-c:a', 'copy'])
        
    cmd.append(str(output_path))
    
    # 捕获渲染日志，拒绝一切暗坑
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg Video Render Failed!\nSTDERR: {result.stderr}")
    
    console.success("Video rendered successfully")