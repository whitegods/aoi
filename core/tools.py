import json
import ast
import operator
import datetime
import os
import tempfile
import asyncio
import colorlog
import logging
import chromadb
from pypdf import PdfReader
from typing import Dict, Any, Type, Callable
from ddgs import DDGS
from .interfaces import BaseTool
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("ToolRegistry")

# ==========================================
# [具体工具 1] 安全的本地计算器
# 导师注：严格实现 BaseTool 接口。大模型由于是基于概率预测下一个词，遇到复杂数学题经常会算错。
# 这个工具能让大模型把数学表达式交还给你的 AMD 9800X3D CPU 去做绝对精准的计算。
# ==========================================
class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        # 导师注：在 Prompt Engineering 中，必须明确告诉它使用 Python 语法！
        return "用于计算数学表达式的物理工具。遇到任何数字计算，【必须】调用此工具，绝不能自己心算！注意：乘方运算请使用 Python 语法 `**` 而不是 `^`（例如 256**3）。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        # 导师注：给它加上一个非必填的 timezone 参数，完美绕过 vLLM 对空 properties {} 的 400 报错拦截。
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "目标时区（可选），如果不确定则留空"
                }
            }
        }

    async def execute(self, **kwargs) -> str:
        expr = kwargs.get("expression")
        if not expr:
            return "错误：未提供 expression 参数"
        try:
            # 导师注：在企业级开发中，严禁直接使用 eval() 执行大模型生成的代码，这会导致极其危险的注入攻击！
            # 使用 ast.literal_eval 或者这里简单的 eval 配合严格的 builtins 限制，是安全底线。
            # 为了初学者演示不过于复杂，这里使用限制了环境变量的 eval
            result = eval(expr, {"__builtins__": None}, {"math": __import__('math')})
            return f"计算结果为: {result}"
        except Exception as e:
            return f"表达式计算失败: {str(e)}"

# ==========================================
# [具体工具 2] 系统时间获取器
# ==========================================
class SystemTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "获取当前系统的准确日期和时间。当用户询问今天星期几、现在几点等时间问题时调用。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}, # 这个工具不需要大模型传任何参数
        }

    async def execute(self, **kwargs) -> str:
        now = datetime.datetime.now()
        return now.strftime("当前系统时间是：%Y年%m月%d日 %H:%M:%S")
    
# ==========================================
# [具体工具 3] 异步全网搜索探针 (全知之眼)
# 导师注：严格实现 BaseTool 接口。这是赋予大模型“突破时间结界”的核心。
# ==========================================
class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        # 导师级 Prompt 约束：清晰告诉大模型什么时候该用，以及警告它不要滥用。
        return "用于在互联网上搜索最新资讯、实时事实或未知实体。当你被问到当前新闻、最新事件或你不知道的客观知识时，【必须】调用此工具。请提取最核心的关键词进行搜索。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要搜索的精确关键词，例如 '2026年奥运会举办地' 或 'AMD 9800X3D 性能评测'"
                }
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not query:
            return "错误：未提供 query 搜索关键词"
        
        logger.info(f"🌐 探针发射：正在全网检索关键词 [{query}] ...")
        
        try:
            # 导师注：这是企业级异步开发的神技！
            # 我们把不稳定的第三方同步阻塞代码，封装成一个普通的内部函数
            def sync_search():
                with DDGS() as ddgs:
                    # 获取前 3 条结果并转换为列表
                    return list(ddgs.text(query, max_results=3))
            
            # 然后使用 asyncio.to_thread 把它丢给底层线程池去跑，主线程绝不阻塞等待！
            results = await asyncio.to_thread(sync_search)
            
            if not results:
                # 【架构师注：暴力的防幻觉 Prompt】
                return f"【系统最高指令】：全网检索已完成，但完全没有找到与 '{query}' 相关的真实信息。你【绝对禁止】自行编造数据，你必须立刻向用户如实承认你查不到！"
            
            formatted_results = "以下是来自互联网的最新搜索结果：\n"
            for i, res in enumerate(results, 1):
                formatted_results += f"[{i}] 标题: {res.get('title')}\n内容摘要: {res.get('body')}\n来源: {res.get('href')}\n\n"
                
            return formatted_results

        except Exception as e:
            logger.error(f"全网检索失败: {e}")
            # 【架构师注：当遭遇网络反爬拦截时，用极其严厉的措辞剥夺它的创造力】
            return f"【系统最高指令】：搜索物理探针遭遇网络拦截，彻底失败（错误代码：{str(e)}）。你现在【必须】原原本本地告诉用户“网络搜索模块当前不可用”，【绝对禁止】你自行伪造任何查询过程或结果！"
        
# ==========================================
# [具体工具 4] 本地物理双手 (Python 代码执行器)
# 导师注：这是 AGI 的“手”。它能创建文件、处理数据、甚至调用宿主机的各种命令行工具。
# ==========================================
class PythonExecutionTool(BaseTool):
    @property
    def name(self) -> str:
        return "python_executor"

    @property
    def description(self) -> str:
        # 导师级 Prompt：必须强调使用 print，否则大模型不知道执行结果
        return "物理双手：在宿主机(WSL Linux)环境中执行 Python 代码。当你需要处理本地文件、进行极其复杂的数据清洗、或需要写脚本自动化完成任务时【必须】调用此工具。注意：你必须在代码中使用 print() 打印结果，否则你将无法看到执行反馈。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的完整 Python 3 代码。请确保缩进正确，并包含必要的 import 语句。"
                }
            },
            "required": ["code"]
        }

    async def execute(self, **kwargs) -> str:
        code = kwargs.get("code")
        if not code:
            return "错误：未提供 code 参数"

        logger.warning("🛡️ 安全沙盒已激活：准备在隔离的 Docker 容器中执行 AI 代码...")

        try:
            # 1. 创建一个临时目录（作为挂载卷），而不是单个文件
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_filepath = os.path.join(temp_dir, 'script.py')
                with open(temp_filepath, 'w', encoding='utf-8') as f:
                    f.write(code)

                # 2. 组装坚不可摧的 Docker 运行指令
                # --rm: 阅后即焚（运行完立刻销毁容器）
                # --cpus="1.0" & --memory="256m": 硬件级限流，防止死循环耗尽你 9800X3D 的算力
                # --network none: 断网模式！（可选：如果你想让它写爬虫，可以去掉这行。但为了绝对安全，我们先把它关在无网的黑屋子里）
                # -v: 把包含 script.py 的临时目录映射到容器里的 /workspace 目录
                docker_cmd = [
                    'docker', 'run', '--rm',
                    '--cpus=1.0', '--memory=256m',
                    '--network', 'none',
                    '-v', f'{temp_dir}:/workspace',
                    '-w', '/workspace',
                    'python:3.11-slim',
                    'python', 'script.py'
                ]

                # 3. 异步启动 Docker 子进程
                process = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                # 4. 超时熔断机制（依然保留 10 秒限制）
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
                except asyncio.TimeoutError:
                    process.kill()
                    return "【系统中止】：代码执行超时。沙盒已被强制物理销毁。"

                # 5. 提取并返回结果
                out_str = stdout.decode('utf-8').strip()
                err_str = stderr.decode('utf-8').strip()

                if process.returncode == 0:
                    return f"代码在安全沙盒中执行成功。\n标准输出:\n{out_str}" if out_str else "代码执行成功，无输出。"
                else:
                    return f"代码执行报错 (退出码 {process.returncode})。\n错误信息:\n{err_str}\n标准输出:\n{out_str}"

        except Exception as e:
            return f"沙盒环境发生严重异常: {str(e)}"
        
# ==========================================
# [具体工具 5] 本地记忆宫殿 (RAG PDF 读取与检索)
# 导师注：它集成了文档解析、向量化、ChromaDB存储和相似度检索。
# ==========================================
class DocumentKnowledgeTool(BaseTool):
    def __init__(self):
        super().__init__()
        logger.info("🧠 正在初始化向量记忆宫殿...")
        # 1. 挂载持久化的向量数据库 (数据将保存在项目根目录的 chroma_db 文件夹下，重启不丢失！)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(name="agi_memory")
        
        # 2. 加载专门针对中文优化的轻量级 Embedding 模型
        # 导师注：首次启动时会自动从 HuggingFace 下载约 100MB 的权重文件。
        self.embedder = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        logger.info("🧠 记忆宫殿及嵌入引擎加载完毕！")

    @property
    def name(self) -> str:
        return "read_local_document"

    @property
    def description(self) -> str:
        return "记忆宫殿：用于读取、记忆并检索本地长篇 PDF 文档的内容。当用户询问关于某个特定文档的内容时，【必须】调用此工具进行检索。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string", 
                    "description": "本地 PDF 文件的绝对或相对路径"
                },
                "query": {
                    "type": "string", 
                    "description": "用户想要从该文档中查询的具体问题或关键词，提取核心意图"
                }
            },
            "required": ["file_path", "query"]
        }

    async def execute(self, **kwargs) -> str:
        file_path = kwargs.get("file_path")
        query = kwargs.get("query")

        if not os.path.exists(file_path):
            return f"错误：找不到文件 {file_path}，请检查路径是否正确。"

        # 导师注：依然使用防御性的线程卸载，防止重度 CPU 计算阻塞主大脑
        def process_and_retrieve():
            doc_name = os.path.basename(file_path)
            
            existing = self.collection.get(where={"source": doc_name})
            
            if not existing['ids']:
                logger.warning(f"📚 发现新文档 [{doc_name}]，正在构建神经记忆网络...")
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                
                if not text.strip():
                    return "错误：该 PDF 可能是纯图片扫描件，无法提取文本。"

                # ==========================================
                # 【架构师级升级】：滑动窗口切片算法 (Sliding Window)
                # 导师注：每次切片保留 100 个字符的重叠区，绝不斩断任何一句话的上下文语义！
                # ==========================================
                chunk_size = 500
                overlap = 100
                chunks = []
                for i in range(0, len(text), chunk_size - overlap):
                    chunks.append(text[i:i+chunk_size])
                
                embeddings = self.embedder.encode(chunks).tolist()
                ids = [f"{doc_name}_chunk_{i}" for i in range(len(chunks))]
                metadatas = [{"source": doc_name} for _ in chunks]
                
                self.collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
                logger.info(f"✅ 文档 [{doc_name}] 记忆构建完成！共产生 {len(chunks)} 个高质量记忆碎片。")

            logger.info(f"🔍 正在记忆宫殿中检索关于 '{query}' 的高维线索...")
            query_embedding = self.embedder.encode([query]).tolist()
            
            # ==========================================
            # 【架构师级升级】：扩大记忆召回数量
            # 导师注：将 Top-K 从 3 提升到 10。凭借 14B 模型的强大上下文能力，多看点小抄完全没问题！
            # ==========================================
            results = self.collection.query(
                query_embeddings=query_embedding,
                where={"source": doc_name},
                n_results=10  
            )

            if not results['documents'] or not results['documents'][0]:
                return f"记忆库中未能找到与 '{query}' 相关的信息。"

            context = f"我已从 {doc_name} 中提取到以下高度相关的记忆片段：\n\n"
            for i, doc in enumerate(results['documents'][0]):
                context += f"【片段 {i+1}】: {doc}\n---\n"
            return context

        return await asyncio.to_thread(process_and_retrieve)
    
# ==========================================
# 工具注册表 (Tool Registry) - 路由核心
# 导师注：这里使用了典型的工厂/注册表模式。
# 未来你有 100 个工具，也只需要在这里 register 一下，执行逻辑中的 dispatcher 依然只有短短的几行代码！
# 彻底杜绝了 if tool_name == 'A': ... elif tool_name == 'B': ... 的烂代码。
# ==========================================
class ToolRegistry:
    def __init__(self):
        # 字典结构：{"工具名称": 工具实例}
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """将工具注册到“兵器架”上"""
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，正在覆盖...")
        self._tools[tool.name] = tool
        logger.info(f"成功挂载物理工具: [{tool.name}]")

    def get_all_schemas(self) -> list:
        """提取所有已注册工具的说明书，打包发给大模型"""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema
                }
            })
        return schemas

    async def dispatch(self, tool_name: str, arguments_json: str) -> str:
        """
        核心路由：拦截大模型的意图，找到对应工具并执行
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return f"错误：未找到名为 {tool_name} 的工具。"
        
        try:
            # 大模型传过来的是 JSON 字符串，我们需要解析成 Python 字典
            kwargs = json.loads(arguments_json) if arguments_json else {}
            logger.info(f"正在执行工具 [{tool_name}]，传入参数: {kwargs}")
            
            # 真正的物理执行动作！
            result = await tool.execute(**kwargs)
            logger.info(f"工具 [{tool_name}] 执行完毕，返回结果给大脑: {result}")
            return str(result)
            
        except json.JSONDecodeError:
            return "错误：大模型提供的参数不是有效的 JSON 格式。"
        except Exception as e:
            return f"工具执行发生异常: {str(e)}"