# ==========================================
# 文件名: tool_weather.py (需放在 Tools 文件夹内)
# 职责: 带有持久化记忆、Open-Meteo 多步查询与【流式思维可视化】的天气管家
# ==========================================

# 🌟 电子铭牌
TOOL_NAME = "🌤️ 贾维斯天气管家 (全能捕获版)"
TOOL_DESC = "支持收藏城市，精准捕获一切 AI 思考痕迹"

import tkinter as tk
from tkinter import scrolledtext
import requests
import json
import os
import ollama

# ==========================================
# 【记忆模块】
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
MEMORIES_DIR = os.path.join(PROJECT_ROOT, "Memories")

if not os.path.exists(MEMORIES_DIR):
    os.makedirs(MEMORIES_DIR)

MEMORY_FILE = os.path.join(MEMORIES_DIR, "weather_memory.json")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"recent": [], "starred": []}

def save_memory(memory_data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=4)

# ==========================================
# 【核心界面与逻辑】
# ==========================================
def run(root_window):
    win = tk.Toplevel(root_window)
    win.title("🛠️ 工具：贾维斯气象站 (全能捕获版)")
    win.geometry("850x550") 

    memory = load_memory()

    left_frame = tk.Frame(win)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    right_frame = tk.Frame(win, width=220, bg="#f0f0f0", relief=tk.SUNKEN, borderwidth=1)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
    right_frame.pack_propagate(False) 

    chat_history = scrolledtext.ScrolledText(left_frame, font=("微软雅黑", 10))
    chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    # 画笔调色板
    chat_history.tag_config("normal_color", foreground="black")
    chat_history.tag_config("think_color", foreground="#888888", font=("微软雅黑", 9, "italic"))
    chat_history.tag_config("sys_color", foreground="blue", font=("微软雅黑", 9, "bold"))
    
    chat_history.insert(tk.END, "🤖 贾维斯：气象卫星已连接。本次挂载 Qwen3.5:4b 并开启思维雷达。\n\n", "sys_color")

    bottom_frame = tk.Frame(left_frame)
    bottom_frame.pack(fill=tk.X)
    input_box = tk.Entry(bottom_frame, font=("微软雅黑", 12))
    input_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

    tk.Label(right_frame, text="📌 收藏与最近查询", font=("微软雅黑", 12, "bold"), bg="#f0f0f0").pack(pady=10)
    history_list_frame = tk.Frame(right_frame, bg="#f0f0f0")
    history_list_frame.pack(fill=tk.BOTH, expand=True)

    def fetch_open_meteo(city):
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh"
        geo_res = requests.get(geo_url, timeout=5).json()
        if not geo_res.get("results"):
            return None, "地球上找不到这个城市的位置信息..."
        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_res = requests.get(weather_url, timeout=5).json()
        temp = weather_res["current_weather"]["temperature"]
        wind = weather_res["current_weather"]["windspeed"]
        return True, f"温度 {temp}°C，风速 {wind} km/h"

    def refresh_right_panel():
        for widget in history_list_frame.winfo_children():
            widget.destroy()
        for city in memory["starred"]:
            row_frame = tk.Frame(history_list_frame, bg="#f0f0f0")
            row_frame.pack(fill=tk.X, pady=2)
            tk.Button(row_frame, text=city, width=12, command=lambda c=city: on_search(c)).pack(side=tk.LEFT, padx=5)
            tk.Button(row_frame, text="⭐", fg="orange", command=lambda c=city: toggle_star(c)).pack(side=tk.LEFT)
        if memory["recent"]:
            tk.Label(history_list_frame, text="--- 最近查询 ---", bg="#f0f0f0", fg="gray").pack(pady=10)
        for city in memory["recent"]:
            row_frame = tk.Frame(history_list_frame, bg="#f0f0f0")
            row_frame.pack(fill=tk.X, pady=2)
            tk.Button(row_frame, text=city, width=12, command=lambda c=city: on_search(c)).pack(side=tk.LEFT, padx=5)
            tk.Button(row_frame, text="☆", fg="gray", command=lambda c=city: toggle_star(c)).pack(side=tk.LEFT)

    def toggle_star(city):
        if city in memory["starred"]:
            memory["starred"].remove(city)
            if city not in memory["recent"]:
                memory["recent"].insert(0, city)
        else:
            if city in memory["recent"]:
                memory["recent"].remove(city)
            if city not in memory["starred"]:
                memory["starred"].append(city)
        save_memory(memory)
        refresh_right_panel()

    def update_memory_with_new_search(city):
        if city in memory["starred"]: return
        if city in memory["recent"]: memory["recent"].remove(city)
        memory["recent"].insert(0, city)
        memory["recent"] = memory["recent"][:5]
        save_memory(memory)
        refresh_right_panel()

    def on_search(target_city=None):
        city = target_city if target_city else input_box.get().strip()
        if not city: return
        
        chat_history.insert(tk.END, f"\n👤 主人: 查询 【{city}】 的天气\n", "normal_color")
        win.update()

        try:
            success, weather_data = fetch_open_meteo(city)
            if not success:
                chat_history.insert(tk.END, f"🤖 贾维斯: {weather_data}\n", "normal_color")
            else:
                chat_history.insert(tk.END, f"☁️ 雷达数据: {weather_data}\n", "sys_color")
                win.update()
                
                # 🌟 【终极紧箍咒】：利用极其严厉的格式限制，逼迫 AI 秒速回答
                prompt = f"""你是一个极其高效的中文贴心管家。
                城市：{city}。气象局数据：{weather_data}。
                【最高系统强制指令】：绝对禁止输出英文，必须严格按照以下格式回复：

                示例：
                <think>
                温度低，风大，重点是防风保暖。
                </think>
                先生，外面寒风刺骨，建议换上重型防风羽绒服。

                现在请回答：
                """
                chat_history.insert(tk.END, f"🤖 贾维斯: \n", "normal_color")
                win.update()

               # 🌟 【引擎升级与参数锁定】
                response_stream = ollama.chat(
                    model='qwen3.5:4b', 
                    messages=[{'role': 'user', 'content': prompt}], 
                    stream=True,
                    options={'temperature': 0.8} # 🌟 核心秘籍1：温度设为0，剥夺它的自由发挥权，绝对服从！
                )
                
                is_thinking = False 
                buffer = "" # 🌟 核心秘籍2：建立“文字缓冲区”，专门对付 Token 撕裂！
                
                for chunk in response_stream:
                    # 获取普通文本通道的内容
                    content_word = chunk['message'].get('content', '')
                    
                    if content_word:
                        buffer += content_word # 别急着打出来，先把字塞进缓冲区攒一攒
                        
                        # 如果缓冲区拼出了完整的开始标签
                        if "<think>" in buffer:
                            chat_history.insert(tk.END, "╭─ [💭 贾维斯大脑运转中] ─╮\n", "think_color")
                            is_thinking = True
                            buffer = buffer.replace("<think>", "") # 把标签从缓冲区抹掉，免得印在屏幕上
                            
                        # 如果缓冲区拼出了完整的结束标签
                        if "</think>" in buffer:
                            chat_history.insert(tk.END, "\n╰─ [💡 思考完毕，得出最优解] ─╯\n\n", "think_color")
                            is_thinking = False
                            buffer = buffer.replace("</think>", "")
                            
                        # ⚠️ 防止“Token撕裂”的关键魔法：
                        # 如果缓冲区里碰巧有个 '<'，而且总字数还很少，说明它极有可能正在吐标签的半截（比如 '<thi'）
                        # 这时候我们“憋着”不输出，让它进入下一次循环，等下一个 chunk 把它拼凑完整！
                        if "<" in buffer and len(buffer) < 10:
                            continue 
                            
                        # 确认安全后，把缓冲区的字画在屏幕上
                        if buffer:
                            if is_thinking:
                                chat_history.insert(tk.END, buffer, "think_color")
                            else:
                                chat_history.insert(tk.END, buffer, "normal_color")
                            buffer = "" # 画完就清空，迎接下一批字
                            
                    # 让滚动条始终保持在最底部
                    chat_history.see(tk.END)
                    win.update()
                
                chat_history.insert(tk.END, "\n\n")
                update_memory_with_new_search(city)
                
        except Exception as e:
            chat_history.insert(tk.END, f"🤖 贾维斯: 抱歉，获取数据或呼叫 AI 失败: {e}\n\n", "normal_color")
            
        input_box.delete(0, tk.END)
        chat_history.see(tk.END)

    win.bind('<Return>', lambda event: on_search())
    send_button = tk.Button(bottom_frame, text="查询", bg="black", fg="white", command=on_search)
    send_button.pack(side=tk.LEFT)

    refresh_right_panel()