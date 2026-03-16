import asyncio
import colorlog
import logging
from core.llm_provider import VLLMClient
from core.memory import ShortTermMemory
from core.tools import ToolRegistry, CalculatorTool, SystemTimeTool
from core.agent import AutonomousAgent

# 配置主程序日志格式
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(message)s'))
logger = logging.getLogger("MainSystem")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

async def main():
    print("\n" + "="*50)
    print("🚀 本地 AGI 核心系统启动中...")
    print("架构：Qwen 14B AWQ + ReAct 认知循环 + 动态工具箱")
    print("="*50 + "\n")

    # 1. 实例化核心组件 (这就是依赖注入的准备阶段)
    llm = VLLMClient()               # 底层引擎网关
    memory = ShortTermMemory()       # 短期记忆模块
    registry = ToolRegistry()        # 动态工具箱
    
    # 2. 注册物理工具 (装配兵器)
    registry.register(CalculatorTool())
    registry.register(SystemTimeTool())

    # 3. 组装终极 Agent (注入依赖)
    agent = AutonomousAgent(
        llm_provider=llm,
        memory=memory,
        tool_registry=registry,
        system_prompt="你是一个极度严谨的本地 AGI 助理。涉及任何数学计算时，你【禁止】自己心算，必须调用 calculator 工具，并严格使用 Python 数学运算符！"
    )
    
    print("\n💬 系统已就绪。你可以开始提问了。(输入 'exit' 或 'quit' 退出)")
    print("-" * 50)

    # 4. 开启 CLI 交互主循环
    while True:
        try:
            user_input = input("\n👤 User: ")
            if user_input.strip().lower() in ['exit', 'quit']:
                print("系统关闭。")
                break
            if not user_input.strip():
                continue
            
            # 异步调用 Agent 大脑
            answer = await agent.chat(user_input)
            
            print(f"\n🤖 AGI: {answer}\n")
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n系统强行关闭。")
            break
        except Exception as e:
            logger.error(f"系统发生致命错误: {e}")

if __name__ == "__main__":
    # 导师注：由于我们的核心全是 async 异步代码，必须通过 asyncio.run() 来启动事件循环
    asyncio.run(main())