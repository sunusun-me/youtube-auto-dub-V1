import asyncio
from .ui import console

# 假设原有的单体翻译函数叫 async def translate_single(text: str, target_lang: str) -> str:
# 或者它有一个现成的批量翻译接口

async def translate_segments(segments: list, target_lang: str) -> list:
    """
    将成百上千个切片进行分批（Chunking）翻译，防止 URL query too long 崩溃
    """
    translated_segments = []
    # 设定每批处理 40 条数据，这个长度绝对不会超出 URL 限制
    chunk_size = 40 
    
    total_segments = len(segments)
    console.info(f"Total segments to translate: {total_segments}. Switching to Chunking Mode...")

    for i in range(0, total_segments, chunk_size):
        chunk = segments[i:i + chunk_size]
        console.info(f"Processing translation chunk: {i // chunk_size + 1}/{(total_segments - 1) // chunk_size + 1}")
        
        # --- 核心修复逻辑：在这里调用你原本的翻译核心 ---
        # 示例一：如果是循环调用单个翻译
        tasks = []
        for seg in chunk:
            # 这里的 translate_single_func 请替换为你脚本里实际的单条翻译函数名
            tasks.append(translate_single_func(seg.text, target_lang)) 
        
        chunk_results = await asyncio.gather(*tasks)
        
        # 将翻译好的文本塞回切片对象中
        for seg, translated_text in zip(chunk, chunk_results):
            seg.translated_text = translated_text
            translated_segments.append(seg)
            
        # 适当给网络引擎 0.5 秒的喘息时间，防止请求过快被风控
        await asyncio.sleep(0.5)
        
    return translated_segments