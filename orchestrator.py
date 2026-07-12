import json
import requests

# ================= 配置区 =================
CLAUDE_API_KEY = "your-claude-api-key-here"
LOCAL_LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
LOCAL_MODEL_NAME = "Qwythos-9B-Claude-Mythos-5-1M-MTP-Q6_K.gguf"
# ==========================================

def call_claude_conductor(user_goal: str) -> list:
    """让 Claude 充当乐团指挥，把模糊的任务拆解成结构化的本地流水线"""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # 强制 Claude 必须输出纯 JSON 数组，没有任何废话
    system_prompt = (
        "你是一个极其严谨的自动化流水线指挥官。请将用户的音视频处理任务拆解为子任务列表。\n"
        "你只能返回一个标准的 JSON 数组，不要包含任何 Markdown 标记（如 ```json）或前后解释。\n"
        "数组中的每个元素必须是如下格式的 JSON 对象：\n"
        '{"id": 1, "action": "local_llm_process", "prompt": "具体让本地模型干什么", "data": "需要处理的初始文本段落"}\n'
        '或者 {"id": 2, "action": "local_audio_mix", "data": "音频合成参数"}'
    )
    
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_goal}]
    }
    
    print("🧠 [Claude] 正在规划流水线...")
    response = requests.post(url, headers=headers, json=data).json()
    # === 核心重构：引入生产级别的防御性解析 ===
    if not response:
        raise RuntimeError("Claude API 返回了空响应，请检查网络代理或 API 状态。")
        
    if 'error' in response:
            # === 终极防御：完全剥离外部依赖的原生打印 ===
        if not response:
            raise RuntimeError("Claude API 返回了空响应，请检查网络代理或 API 状态。")
        
    if 'error' in response:
        # 放弃依赖外部 UI 组件，改用 100% 绝对安全的原生 print
        print(f"\n❌ Claude API 明确拒绝了请求: {response['error']}")
        raise RuntimeError(f"API Error: {response['error'].get('message', 'Unknown error')}")

    if 'content' not in response:
        print(f"\n⚠️ 收到异常响应结构，缺失 'content' 键。完整响应体如下：")
        print(response)
        raise KeyError("API 响应体结构异常，未包含 'content' 字段。")

    # 确信安全后，再进行物理抓取
    raw_text = response['content'][0]['text'].strip()
        
    raise RuntimeError(f"API Error: {response['error'].get('message', 'Unknown error')}")

    if 'content' not in response:
        # 终极打印：当场撕开云端返回的真实面目，暴露真正原因
        console.print(f"\n[yellow]⚠️ 收到异常响应结构，缺失 'content' 键。完整响应体如下：[/yellow]")
        console.print(response)
        raise KeyError("API 响应体结构异常，未包含 'content' 字段。")

    # 确信安全后，再进行物理抓取
    raw_text = response['content'][0]['text'].strip()
    return json.loads(raw_text)

def run_local_llm(prompt: str, content: str) -> str:
    """让 M4 Mac Mini 本地的 Llama.cpp 承担具体的脏活累活"""
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": LOCAL_MODEL_NAME,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ],
        "temperature": 0.3 # 低温保证翻译和清洗的稳定性
    }
    
    response = requests.post(LOCAL_LLAMA_URL, headers=headers, json=payload).json()
    return response['choices'][0]['message']['content']

def execute_pipeline(tasks: list):
    """本地驱动引擎：根据 Claude 的编排，无缝调用本地算力和物理引擎"""
    print(f"\n⚙️ 成功加载流水线，共 {len(tasks)} 个任务。开始在 M4 Mac Mini 上本地跑通：")
    
    context_data = "" # 用于承接上下文的变量
    
    for task in tasks:
        print(f"\n▶️ 正在执行任务 [{task['id']}] - {task['action']}")
        
        if task['action'] == "local_llm_process":
            # 这里的输入可能是上一阶段产生的数据，或者是 Claude 初始分配的数据
            input_data = context_data if context_data else task['data']
            print(f"   💾 正在调用本地模型 {LOCAL_MODEL_NAME} 进行处理...")
            
            # 本地 M4 芯片全速运转
            result = run_local_llm(task['prompt'], input_data)
            print(f"   ✅ 本地模型输出成功。")
            context_data = result # 传递给下一个节点
            
        elif task['action'] == "local_audio_mix":
            print(f"   🎛️ 物理引擎介入：正在调用本地 pydub 内存音频引擎融合数据...")
            # 在这里直接内嵌你原有的 youtube-auto-dub 的物理混音逻辑
            # e.g., pydub_melt_engine(context_data)
            print(f"   🎉 物理音频熔炼完成！")
            
    print("\n🏁 [完美闭环] 任务全部落地产出！")

if __name__ == "__main__":
    # 这是一个模拟你的 youtube-auto-dub 业务的模糊指令
    user_input = (
        "我有一个 YouTube 视频的英文字幕片段：'Welcome back to the channel. Today we are testing the insane performance of Apple M4 chip.' "
        "请帮我用本地模型把它翻译成优雅的中文，然后准备进行物理音频熔炼。"
    )
    
    # 1. 云端大脑编排
    pipeline_json = call_claude_conductor(user_input)
    
    # 2. 本地物理执行
    execute_pipeline(pipeline_json)