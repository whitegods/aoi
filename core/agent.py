import json
import logging
from typing import Optional

import colorlog
from .interfaces import BaseLLMProvider, BaseMemory, Message
from .tools import ToolRegistry

logger = logging.getLogger("AgentBrain")

# ==========================================
# 终极自主智能体 (Autonomous Agent)
# 导师注：这里完美展示了 DIP (依赖倒置原则) 和依赖注入 (Dependency Injection)。
# Agent 初始化时，我们把实现了接口的实例“塞”给它。它只管调用标准接口，完全不在乎底层是怎么实现的。
# ==========================================
class AutonomousAgent:
    def __init__(self, 
                 llm_provider: BaseLLMProvider, 
                 memory: BaseMemory, 
                 tool_registry: ToolRegistry,
                 system_prompt: str = "你是一个强大的本地 AGI 系统，请尽力帮助用户。遇到不确定的事情，优先考虑使用工具。"):
        
        self.llm = llm_provider
        self.memory = memory
        self.tools = tool_registry
        
        # 初始化时，先给记忆里塞入“系统人设” (System Prompt)
        self.memory.add_message(Message(role="system", content=system_prompt))
        logger.info("Agent 大脑初始化完成，各模块已成功挂载！")

    async def chat(self, user_input: str, image_base64: Optional[str] = None) -> str:
        """与 Agent 进行一次完整的对话交互"""
        # 【架构师级修复】：死死捏住图片数据，把它刻进短时记忆里！
        self.memory.add_message(Message(
            role="user", 
            content=user_input, 
            image_base64=image_base64  # <--- 绝对不能漏掉这一行！！！
        ))
        
        # ... (下方原来的 max_loops = 5 等核心认知循环代码完全不变) ...
        
        # 提取当前所有可用的工具说明书
        available_tools = self.tools.get_all_schemas() if self.tools._tools else None
        
        # ==========================================
        # 核心认知循环 (The ReAct Loop)
        # 导师注：大模型可能需要连续调用多个工具（比如先查天气，再查日历，最后总结）。
        # 所以这必须是一个 while 循环，直到大模型认为不需要工具、直接输出文本为止。
        # ==========================================
        max_loops = 5  # 设置最大思考循环次数，防止大模型陷入死循环
        loop_count = 0
        
        while loop_count < max_loops:
            loop_count += 1
            logger.info(f"--- 开启第 {loop_count} 轮认知思考 ---")
            
            # 2. 思考 (Think)：将所有记忆和工具发给大模型
            context = self.memory.get_context()
            response_msg = await self.llm.generate_response(messages=context, tools=available_tools)
            
            # 必须把大模型的原始回复存入记忆，保持上下文的连贯性
            self.memory.add_message(response_msg)
            
            # 3. 观察与行动 (Observe & Act)：判断大模型是否决定使用工具
            if response_msg.tool_calls:
                logger.warning(f"💡 大模型触发了工具调用意图！共 {len(response_msg.tool_calls)} 个动作。")
                
                # 遍历执行大模型要求的所有工具
                for tool_call in response_msg.tool_calls:
                    tool_call_id = tool_call.get("id")
                    function_details = tool_call.get("function", {})
                    tool_name = function_details.get("name")
                    tool_args = function_details.get("arguments")
                    
                    # 将执行指令丢给动态工具箱，获取物理执行结果
                    tool_result_str = await self.tools.dispatch(tool_name, tool_args)
                    
                    # 4. 反馈 (Feedback)：将工具的执行结果打包成特殊的 tool 角色消息，塞回记忆中
                    # 导师注：这是 OpenAI 格式的铁律，必须带有 tool_call_id，大模型才能把结果和之前的请求对应起来。
                    tool_feedback_msg = Message(
                        role="tool", 
                        content=tool_result_str,
                        tool_call_id=tool_call_id
                    )
                    self.memory.add_message(tool_feedback_msg)
                
                # 工具执行完毕，记忆已更新，进入下一轮 while 循环，让大模型看着结果继续思考
                continue 
            
            else:
                # 如果没有 tool_calls，说明大模型觉得信息够了，直接输出了最终回答
                logger.info("✅ 认知循环结束，生成最终回答。")
                return response_msg.content
                
        return "警告：Agent 思考次数超过上限，已强制中断。"