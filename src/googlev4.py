import json
import re
import httpx
import asyncio
import random
from typing import List
from bs4 import BeautifulSoup
from .ui import console

class GoogleTranslator:
    def __init__(self):
        # 提高超时阈值，防止长句翻译时网络波动导致配音音轨直接断裂
        self.client = httpx.AsyncClient(timeout=20)
        self.fallback_count = 0  # 记录翻译失败回退原文的段数(隐蔽错误显性化)
        self.base_url_rpc = "https://translate.google.com/_/TranslateWebserverUi/data/batchexecute"
        self.base_url_scrape = "https://translate.google.com/m"
        
        # 建立动态 User-Agent 矩阵，从根源上欺骗流量审查
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ]
        self.headers = {"User-Agent": self.user_agents[0]}
        self.bl = None

    async def _refreshRpcToken(self):
        headers = {"User-Agent": random.choice(self.user_agents)}
        try:
            response = await self.client.get("https://translate.google.com/", headers=headers)
            bl_match = re.search(r'"cfb2h":"(.*?)"', response.text)
            if bl_match:
                self.bl = bl_match.group(1)
            else:
                self.bl = "boq_translate-webserver_20260301.01_p0"
        except Exception as e:
            console.warning(f"Token refresh failed: {e}. Using fallback.")
            self.bl = "boq_translate-webserver_20260301.01_p0"

    async def _parseRpcResponse(self, raw_text):
        try:
            match = re.search(r'\["wrb.fr","MkEWBc","(.*?)",null,null,null,"generic"\]', raw_text, re.DOTALL)
            if not match: 
                raise ValueError("Could not find translation data in RPC response.")
            inner_json_str = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
            data = json.loads(inner_json_str)
            translation_parts = data[1][0][0][5]
            final_text = "".join([part[0] for part in translation_parts if part[0]])
            return final_text
        except Exception as e:
            raise ValueError(f"RPC Parse Error: {e}")

    async def _translateRpc(self, text, source, target):
        if not self.bl:
            await self._refreshRpcToken()
        
        rpc_arg = json.dumps([[text, source, target, True, [1]]], ensure_ascii=False)
        f_req = json.dumps([["MkEWBc", rpc_arg, None, "generic"]])

        params = {
            "rpcids": "MkEWBc",
            "bl": self.bl,
            "hl": "en",
            "rt": "c"
        }
        
        headers = {"User-Agent": random.choice(self.user_agents)}
        response = await self.client.post(
            self.base_url_rpc, 
            headers=headers, 
            params=params, 
            data={"f.req": f_req}
        )

        if response.status_code != 200:
            raise Exception(f"RPC HTTP Error: {response.status_code}")
        
        return await self._parseRpcResponse(response.text)

    async def _translateScrape(self, text, source, target):
        params = {
            "sl": source,
            "tl": target,
            "q": text
        }
        headers = {"User-Agent": random.choice(self.user_agents)}
        response = await self.client.get(self.base_url_scrape, params=params, headers=headers)
        
        if response.status_code == 429:
            raise Exception("Too Many Requests (429)")
        if response.status_code != 200:
            raise Exception(f"Scrape HTTP Error: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.find("div", {"class": "t0"})
        if not element:
            element = soup.find("div", {"class": "result-container"})
        if not element:
            raise Exception("Could not find translation element in HTML.")
            
        return element.get_text(strip=True)

    async def translate(self, text, source="auto", target="zh-CN"):
        """
        单句原子翻译核心：具备内置指数退避重试和多路防御机制
        """
        if not text or not text.strip():
            return ""
            
        # 自动纠正主程序传入的非标准中文缩写
        tgt = "zh-CN" if target.lower() in ["zh-cn", "zh"] else target
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 优先尝试更干净的官方网页级 RPC 模拟
                return await self._translateRpc(text, source, tgt)
            except Exception:
                try:
                    # 遭遇阻碍后，平滑退化为移动端 Scrape 引擎机制
                    return await self._translateScrape(text, source, tgt)
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        # 遭遇 429 频率限制时启动动态退让延迟
                        sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(sleep_time)
                        continue
                    else:
                        last_error = e

        # 降级返回原文保障流水线不断, 但必须显性告警(禁止静默污染下游)
        self.fallback_count += 1
        console.warning(f"[翻译回退] 第 {self.fallback_count} 段翻译失败, 回退原文: {text[:40]!r}...")
        return text

    async def translate_batch(self, texts: List[str], target: str) -> List[str]:
        """
        基于 M4 高性能架构彻底重构的分布式流式批量处理引擎。
        彻底抛弃高风险的拼接符号（Delimiter），采用可控的异步并发信道。
        """
        if not texts:
            return []

        # 针对 839 句这种庞大体量的长视频，设立安全的 5 并发信道池
        sem = asyncio.Semaphore(5)
        total_count = len(texts)
        
        console.info(f"⚡ [M4 优化引擎] 已彻底抛弃拼接符号，正在通过分布式信道并发处理 {total_count} 个文本切片...")

        # 进度追踪闭包
        counter = 0
        async def worker(index: int, text: str) -> tuple:
            nonlocal counter
            async with sem:
                # 在请求前加入极其微弱的随机扰动（10~50ms），破坏高频机器行为特征
                await asyncio.sleep(random.uniform(0.01, 0.05))
                
                translated = await self.translate(text, source="auto", target=target)
                
                counter += 1
                if counter % 50 == 0 or counter == total_count:
                    console.info(f" -> 已平滑洗完翻译数据: {counter}/{total_count} 条...")
                
                return index, translated

        # 为所有待翻译文本打上索引标记，防止 asyncio 异步收拢时导致语序错位
        tasks = [worker(idx, text) for idx, text in enumerate(texts)]
        
        # 并发执行
        indexed_results = await asyncio.gather(*tasks)
        
        # 严格按照原数组的索引进行完美物理对齐（绝无对齐失败可能）
        sorted_results = sorted(indexed_results, key=lambda x: x[0])
        final_results = [res[1] for res in sorted_results]

        if self.fallback_count:
            console.warning(f"[WARN] 本批共 {self.fallback_count}/{total_count} 段翻译失败回退原文, 产物可能混入源语言!")

        return final_results

    async def close(self):
        await self.client.aclose()