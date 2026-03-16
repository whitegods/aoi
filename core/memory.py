from typing import List
from .interfaces import BaseMemory, Message

# ==========================================
# 短期记忆实现类
# 导师注：它只负责一件事——管理对话数组。纯粹且高效。
# ==========================================
class ShortTermMemory(BaseMemory):
    def __init__(self):
        # 使用 Type Hints 明确这是一个存放 Message 对象的列表
        self.messages: List[Message] = []

    def add_message(self, message: Message) -> None:
        """向记忆中追加一条新消息"""
        self.messages.append(message)

    def get_context(self) -> List[Message]:
        """获取当前所有的上下文记忆"""
        return self.messages

    def clear(self) -> None:
        """清空记忆，防止上下文超载 (OOM)"""
        self.messages.clear()