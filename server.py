import logging
import colorlog
import base64
import os
import edge_tts
from fastapi.responses import Response
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# ==========================================
# 导入我们引以为傲的底层 AGI 核心模块
# 导师注：得益于我们前期的解耦设计，这里我们直接复用所有的核心类，一行底层逻辑都不用改！
# ==========================================
from core.llm_provider import VLLMClient
from core.memory import ShortTermMemory
from core.tools import ToolRegistry, CalculatorTool, SystemTimeTool, WebSearchTool, PythonExecutionTool, DocumentKnowledgeTool
from core.agent import AutonomousAgent

# 配置日志
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)s - [%(levelname)s] - %(message)s'))
logger = logging.getLogger("APIServer")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ==========================================
# 初始化 Web 框架与跨域策略 (CORS)
# ==========================================
app = FastAPI(title="AGI 核心中枢 API", version="1.0.0")

# 导师注：前端运行在浏览器里（通常是 localhost:3000），而后端运行在 8080 端口。
# 浏览器的同源策略会默认拦截这种跨端口请求。配置 CORS 就是为了给前端发放“通行证”。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许任何前端页面访问（生产环境应设为具体的域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许 GET, POST 等所有 HTTP 方法
    allow_headers=["*"],
)

# ==========================================
# 依赖注入：在服务器启动时，单例实例化所有核心组件
# ==========================================
logger.info("正在将 Agent 大脑装载入 Web 容器...")
llm = VLLMClient()
memory = ShortTermMemory()
registry = ToolRegistry()
registry.register(CalculatorTool())
registry.register(SystemTimeTool())
registry.register(WebSearchTool())
registry.register(PythonExecutionTool())
registry.register(DocumentKnowledgeTool())

agent = AutonomousAgent(
    llm_provider=llm,
    memory=memory,
    tool_registry=registry,
    system_prompt="你是一个极度严谨的多模态原生 AGI。你不仅能进行物理运算和全网搜索，你还拥有完美的视觉能力！当用户发来图片时，你必须仔细观察并如实描述细节，绝对不要说你看不见图片，也绝对不要凭空捏造！"
)

# ==========================================
# 定义前端与后端的“通信契约” (DTO - Data Transfer Object)
# ==========================================
class ChatRequest(BaseModel):
    message: str
    image_base64: Optional[str] = None  # <--- 【新增】：允许前端传图片 Base64

class ChatResponse(BaseModel):
    reply: str

class TTSRequest(BaseModel):
    text: str

# 2. 升级路由处理
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"📩 收到前端用户消息: {request.message} [是否带图: {bool(request.image_base64)}]")
        
        # ==========================================
        # 【架构师级抓包测试】：把发给大模型之前的图片，强行保存在本地！
        # ==========================================
        if request.image_base64:
            try:
                # 剥离掉可能存在的 data:image/jpeg;base64, 前缀
                b64_str = request.image_base64.split(",")[-1]
                with open("debug_vision.jpg", "wb") as f:
                    f.write(base64.b64decode(b64_str))
                logger.info("📸 [拦截测试] 已将前端传来的图片保存为 debug_vision.jpg，请在 VSCode 里打开看看！")
            except Exception as e:
                logger.error(f"❌ [拦截测试] 图片解码失败，前端传来的数据已损坏: {e}")
        # ==========================================
                
        # 唤醒异步认知循环！
        answer = await agent.chat(request.message, request.image_base64)
        
        logger.info(f"📤 准备回复前端: {answer[:20]}...")
        return ChatResponse(reply=answer)
        
    except Exception as e:
        logger.error(f"Agent 处理 API 请求时发生异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    【架构师级黑科技】：纯内存异步音频流生成，不写硬盘，极致极速！
    """
    try:
        # 使用微软的中文极品音色 (晓晓 - 情感女声)
        # 你也可以换成 "zh-CN-YunxiNeural" (阳光男声)
        communicate = edge_tts.Communicate(request.text, "zh-CN-XiaoxiaoNeural")
        
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
                
        # 直接将二进制音频流返回给前端！
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        raise HTTPException(status_code=500, detail="Voice module offline")