import httpx
import logging
from typing import List, Dict, Any, Optional

import colorlog
from .interfaces import BaseLLMProvider, Message

# ==========================================
# [企业级日志配置] 
# 导师注：在没有 UI 的阶段，五颜六色的控制台日志是我们洞察系统内部运行状态的唯一途径。
# ==========================================
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - [%(levelname)s] - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))
logger = logging.getLogger("VLLMClient")
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ==========================================
# VLLM 异步网关实现
# 导师注：严格实现 BaseLLMProvider 接口。包含完整的 Try-Catch 错误处理。
# ==========================================
class VLLMClient(BaseLLMProvider):
    def __init__(self, 
                 base_url: str = "http://localhost:8000/v1", 
                 api_key: str = "agi-secret-key", 
                 model_name: str = "Qwen/Qwen2.5-14B-Instruct-AWQ"):
        
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_response(self, messages: List[Message], tools: Optional[List[Dict[str, Any]]] = None) -> Message:
        formatted_messages = []
        
        # 1. 寻找当前这一轮对话中，最新的一条 User 消息
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            # 兼容对象模式或字典模式
            role = getattr(messages[i], 'role', messages[i].get('role') if isinstance(messages[i], dict) else None)
            if role == "user":
                last_user_idx = i
                break
                
        # 2. 【架构师级鲁棒提取】：无论它是对象还是字典，绝不漏掉一滴像素！
        image_data = None
        if last_user_idx != -1:
            msg = messages[last_user_idx]
            if hasattr(msg, 'image_base64') and msg.image_base64:
                image_data = msg.image_base64
            elif isinstance(msg, dict) and msg.get('image_base64'):
                image_data = msg['image_base64']

        is_active_vision = bool(image_data)

        if is_active_vision:
            logger.warning("👁️ 活跃视觉信号接入！执行【指令融合】，开启绝对纯净单轮视界...")
            # 1. 提取思想钢印
            system_text = ""
            if messages and getattr(messages[0], 'role', messages[0].get('role') if isinstance(messages[0], dict) else None) == "system":
                sys_content = getattr(messages[0], 'content', messages[0].get('content') if isinstance(messages[0], dict) else "")
                system_text = f"【系统最高指令：{sys_content}】\n\n用户问题："
                
            # 2. 获取用户提问内容
            msg_content = getattr(msg, 'content', msg.get('content') if isinstance(msg, dict) else "")
                
            formatted_messages = [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}},
                    {"type": "text", "text": system_text + msg_content}
                ]
            }]
            
            payload = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": 0.1,  
                "max_tokens": 2048
            }
        else:
            # ==========================================
            # 【常规逻辑通道】：恢复所有记忆与工具箱
            # ==========================================
            for i, msg in enumerate(messages):
                # 顺手做个记忆清理：如果历史对话里有图片，强行卸载变成文字，防止未来的对话被污染
                if getattr(msg, 'image_base64', None) and i != last_user_idx:
                    safe_content = "[系统提示：用户曾在此处上传图片，现已从上下文安全卸载] \n" + msg.content
                    msg_dict = {"role": msg.role, "content": safe_content}
                else:
                    msg_dict = {"role": msg.role, "content": msg.content}
                    
                if getattr(msg, 'tool_calls', None):
                    msg_dict["tool_calls"] = msg.tool_calls
                if getattr(msg, 'tool_call_id', None):
                    msg_dict["tool_call_id"] = msg.tool_call_id
                formatted_messages.append(msg_dict)
                
            payload = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": 0.3,
                "max_tokens": 2048
            }
            if tools:
                payload["tools"] = tools

        logger.info(f"正在向大模型发送请求... 载荷模式: {'👁️ 纯净视觉' if is_active_vision else '🧠 认知推理'}")

        # 发起异步网络请求 (后续代码不变)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status() 
                result = response.json()
                choice = result["choices"][0]["message"]
                
                return Message(
                    role=choice.get("role", "assistant"),
                    content=choice.get("content") or "",  
                    tool_calls=choice.get("tool_calls")
                )
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"被大模型网关拒绝 (状态码 {e.response.status_code})。详细退回原因: {error_detail}")
            raise RuntimeError(f"数据格式不匹配: {error_detail}")
        except Exception as e:
            logger.error(f"解析大模型认知数据时发生不可预知的错误: {e}")
            raise