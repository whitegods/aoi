# ==========================================
# 文件名: main_hub.py (AGI 进化版：NVIDIA 官方引擎监控中枢)
# 职责: 带有实时硬件监测(pynvml)、动态回收、极客 UI 的中枢
# ==========================================

import tkinter as tk
import os
import importlib
import requests
import threading 
import time
import psutil 
# 🌟 【引擎升级】导入 NVIDIA 官方显卡监控库
import pynvml 

def load_all_tools():
    """扫描 Tools 文件夹下的武器库模块"""
    loaded_tools = [] 
    current_folder = os.path.dirname(os.path.abspath(__file__))
    tools_folder = os.path.join(current_folder, "Tools")
    
    if not os.path.exists(tools_folder):
        os.makedirs(tools_folder)
        return loaded_tools
        
    for filename in os.listdir(tools_folder):
        if filename.startswith("tool_") and filename.endswith(".py"):
            module_name = filename[:-3] 
            try:
                import_path = f"Tools.{module_name}"
                module = importlib.import_module(import_path)
                tool_info = {
                    "name": module.TOOL_NAME,      
                    "desc": module.TOOL_DESC,      
                    "action": module.run           
                }
                loaded_tools.append(tool_info)
            except Exception as e:
                print(f"❌ 挂载 {filename} 失败: {e}")
                
    return loaded_tools

class JARVISHub:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧠 J.A.R.V.I.S. 中枢控制台 v0.3 (NVML版)")
        self.root.geometry("600x550")
        self.root.configure(bg="#0a0a0a")
        
        # 顶部状态显示区域
        self.status_frame = tk.Frame(self.root, bg="#111", pady=10)
        self.status_frame.pack(fill=tk.X)
        
        self.cpu_label = tk.Label(self.status_frame, text="CPU: --%", bg="#111", fg="#00ff00", font=("Consolas", 10))
        self.cpu_label.pack(side=tk.LEFT, padx=20)
        
        self.ram_label = tk.Label(self.status_frame, text="RAM: --%", bg="#111", fg="#00ff00", font=("Consolas", 10))
        self.ram_label.pack(side=tk.LEFT, padx=20)
        
        self.gpu_label = tk.Label(self.status_frame, text="GPU VRAM: 正在初始化神经连接...", bg="#111", fg="#00e5ff", font=("Consolas", 10, "bold"))
        self.gpu_label.pack(side=tk.LEFT, padx=20)

        # 加载工具
        self.available_tools = load_all_tools()
        self.setup_ui()
        
        # 启动后台监控线程
        self.keep_monitoring = True
        self.monitor_thread = threading.Thread(target=self.update_stats_loop, daemon=True)
        self.monitor_thread.start()

        # 绑定退出事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_stats_loop(self):
        """每隔一秒，探测一次硬件的生命体征"""
        
        # 🌟 尝试唤醒 NVIDIA 底层驱动
        try:
            pynvml.nvmlInit()
            nvml_initialized = True
        except Exception as e:
            nvml_initialized = False
            print(f"⚠️ NVIDIA 驱动通信失败: {e}")

        while self.keep_monitoring:
            try:
                # 获取 CPU 和内存百分比
                cpu_p = psutil.cpu_percent()
                ram_p = psutil.virtual_memory().percent
                
                gpu_text = "GPU: 未连接"
                # 🌟 如果 NVIDIA 驱动唤醒成功，开始精准窃取显存数据
                if nvml_initialized:
                    # 抓取第一块显卡（索引为 0，即你的 RTX 5080）的控制柄
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    # 读取显存信息
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    # pynvml 返回的是 Byte (字节)，我们要把它除以两个 1024 转换成 MB
                    # 1024 * 1024 就是 1024**2
                    used_mb = mem_info.used / (1024**2)
                    total_mb = mem_info.total / (1024**2)
                    
                    # 格式化成没有小数点的整数
                    gpu_text = f"RTX 5080 VRAM: {used_mb:.0f}MB / {total_mb:.0f}MB"
                
                # 发回主界面更新显示
                self.root.after(0, self.refresh_labels, cpu_p, ram_p, gpu_text)
                
                time.sleep(1) 
            except Exception:
                pass
                
        # 🌟 退出时关闭 NVIDIA 驱动连接，释放系统资源
        if nvml_initialized:
            pynvml.nvmlShutdown()

    def refresh_labels(self, cpu, ram, gpu):
        """把采集到的数据画在屏幕上"""
        self.cpu_label.config(text=f"CPU: {cpu}%")
        self.ram_label.config(text=f"RAM: {ram}%")
        self.gpu_label.config(text=gpu)

    def setup_ui(self):
        title_label = tk.Label(self.root, text="J.A.R.V.I.S. 协议模块", font=("微软雅黑", 18, "bold"), bg="#0a0a0a", fg="#00e5ff")
        title_label.pack(pady=30)
        
        if not self.available_tools:
            tk.Label(self.root, text="⚠️ 模块库为空", bg="#0a0a0a", fg="red").pack()
        else:
            for tool in self.available_tools:
                card = tk.Frame(self.root, bg="#1c1c1c", pady=10)
                card.pack(fill=tk.X, padx=40, pady=8)
                
                btn = tk.Button(card, text=tool["name"], font=("微软雅黑", 12, "bold"), 
                                bg="#00e5ff", fg="black", activebackground="#00b8cc",
                                relief=tk.FLAT, width=20,
                                command=lambda a=tool["action"]: a(self.root))
                btn.pack(side=tk.LEFT, padx=15)
                
                tk.Label(card, text=tool["desc"], font=("微软雅黑", 9), bg="#1c1c1c", fg="#888888").pack(side=tk.LEFT)

    def on_closing(self):
        """休眠指令：清理显存雷达"""
        self.keep_monitoring = False # 停止监控线程
        print("\n🛑 接收到休眠指令，正在扫描残留模型...")
        try:
            response = requests.get("http://localhost:11434/api/ps", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                for m in models:
                    name = m['name']
                    print(f"🧹 回收显存: {name}...")
                    requests.post("http://localhost:11434/api/generate", json={"model": name, "keep_alive": 0}, timeout=2)
        except Exception:
            pass
        print("✅ J.A.R.V.I.S. 已进入休眠。")
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    hub = JARVISHub()
    hub.run()