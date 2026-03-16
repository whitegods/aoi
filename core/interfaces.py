import abc
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# ==========================================
# [实体定义] 数据传输对象 (DTO - Data Transfer Object)
# 导师解释：我们不使用普通的 Python 字典来传递消息，而是使用 Pydantic 的 BaseModel。
# 这样做的好处是“类型安全”。如果你不小心把 role 拼成了 rool，代码在运行前就会报错，
# 彻底杜绝了低级 Bug，这是系统健壮性的第一道防线。
# ==========================================
class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    # 【必须有这行】：否则图片数据无处安放！
    image_base64: Optional[str] = None

# ==========================================
# [接口 1] 底层大模型网关层 (LLM Provider)
# 导师解释：这里应用了 SOLID 中的 DIP (依赖倒置原则)。
# Agent 大脑只认识 BaseLLMProvider，它不知道背后是 vLLM 还是 OpenAI。
# abc.ABC 代表“抽象基类”，强制要求子类必须实现 @abc.abstractmethod 装饰的方法。
# ==========================================
class BaseLLMProvider(abc.ABC):
    
    @abc.abstractmethod
    async def generate_response(self, messages: List[Message], tools: Optional[List[Dict[str, Any]]] = None) -> Message:
        """
        异步生成大模型的回复。
        :param messages: 历史对话列表
        :param tools: 可供大模型使用的工具 JSON Schema 列表
        :return: 返回一个标准的 Message 对象
        """
        pass

# ==========================================
# [接口 2] 记忆管理子系统 (Memory Management)
# 导师解释：应用了 SRP (单一职责原则)。记忆的存储、修剪、持久化全归它管。
# ==========================================
class BaseMemory(abc.ABC):
    
    @abc.abstractmethod
    def add_message(self, message: Message) -> None:
        """向记忆中追加一条新消息"""
        pass

    @abc.abstractmethod
    def get_context(self) -> List[Message]:
        """获取当前格式化后的所有上下文记忆"""
        pass
    
    @abc.abstractmethod
    def clear(self) -> None:
        """清空记忆"""
        pass

# ==========================================
# [接口 3] 动态工具箱 (Tool & Action)
# 导师解释：应用了 OCP (开闭原则) 和策略模式。
# 每一个工具都是一个独立的类，必须实现这个接口。这样增加新工具时，核心主循环一行代码都不用改。
# ==========================================
class BaseTool(abc.ABC):
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """工具的英文名称，只允许字母、数字、下划线 (给大模型看的)"""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """工具的详细描述 (决定了模型是否能准确理解并调用它)"""
        pass

    @property
    @abc.abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """工具参数的 JSON Schema 定义"""
        pass

    @abc.abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        异步执行工具的实际逻辑
        :param kwargs: 大模型传入的参数
        :return: 工具执行结果的字符串
        """
        pass