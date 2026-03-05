# ==========================================
# 文件名: tool_weather.py (需放在 Tools 文件夹内)
# 职责: 带有持久化记忆、Open-Meteo 实时查询、流式思维与【语音发声引擎】的天气管家
# ==========================================

# 🌟 隐藏 pygame 每次启动时烦人的欢迎语，保持控制台纯净
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

TOOL_NAME = "🌤️ 贾维斯气象雷达 (语音播报版)"
TOOL_DESC = "搭载 Qwen2.5:14b 与 Edge-TTS 神经网络发声引擎"

import tkinter as tk
from tkinter import scrolledtext
import requests
import json
import ollama
# 🌟 新增的发声引擎依赖
import asyncio
import edge_tts
import pygame
import threading
import time

# ==========================================
# 【发声模块 (Voice Protocol) - GPT-SoVITS 终极硬核版】
# ==========================================
def jarvis_speak(text):
    """
    呼叫本地 RTX 5080 上的 GPT-SoVITS 引擎进行声音克隆。
    """
    def _speak_thread():
        try:
            clean_text = text.replace('\n', '。')
            audio_file = "jarvis_clone_reply.wav"
            
            # 🌟 这里的参数必须和你自己准备的音频完全一致！
            # 请根据你的实际情况修改下面这两个变量：
            ref_audio_path = "jarvis.wav"  # 你放在 GPT-SoVITS 根目录下的音频文件名
            prompt_text = "Good morning. It's 7:00 a.m. The weather in Malibu is 72 degrees with scattered clouds. The surf conditions are fair with waist-to-shoulder high lines. For you, Sir, always." # 那段音频里贾维斯到底说了什么字
            
            # 向本地引擎发送极其严密的克隆请求
            api_url = "http://127.0.0.1:9880/"
            params = {
                "text": clean_text,                   # AI 生成的最新天气播报
                "text_lang": "zh",                    # 播报语言
                "ref_audio_path": ref_audio_path,     # 贾维斯的“声音基因”样本
                "prompt_text": prompt_text,           # 样本对应的文字
                "prompt_lang": "en"                   # 样本的语言
            }
            
            print("🚀 正在向 RTX 5080 发送声音克隆指令...")
            # 发送请求，允许它有 30 秒的合成时间
            response = requests.get(api_url, params=params, timeout=30)
            
            if response.status_code == 200:
                with open(audio_file, "wb") as f:
                    f.write(response.content)
            else:
                print(f"⚠️ 引擎拒绝请求，状态码: {response.status_code}，报错: {response.text}")
                return 
            
            # 召唤 pygame 播放
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # 打扫战场
            pygame.mixer.quit()
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
        except requests.exceptions.ConnectionError:
            print("⚠️ 无法连接到引擎！请确保你已经双击运行了 Start_Jarvis_API.bat")
        except Exception as e:
            print(f"⚠️ 语音克隆模块遭遇未知错误: {e}")

    threading.Thread(target=_speak_thread, daemon=True).start()

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
    win.title("🛠️ 贾维斯终端控制台 (J.A.R.V.I.S. Protocol)")
    win.geometry("900x600") 
    win.configure(bg="#0a0a0a") 

    memory = load_memory()

    left_frame = tk.Frame(win, bg="#0a0a0a")
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    right_frame = tk.Frame(win, width=220, bg="#1c1c1c", relief=tk.SUNKEN, borderwidth=1)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
    right_frame.pack_propagate(False) 

    chat_history = scrolledtext.ScrolledText(left_frame, font=("微软雅黑", 11), bg="#0a0a0a", fg="#00ff00", insertbackground="white")
    chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    chat_history.tag_config("normal_color", foreground="#00e5ff") 
    chat_history.tag_config("think_color", foreground="#555555", font=("微软雅黑", 10, "italic")) 
    chat_history.tag_config("sys_color", foreground="#ffb300", font=("微软雅黑", 10, "bold")) 
    chat_history.tag_config("user_color", foreground="#ffffff") 
    
    chat_history.insert(tk.END, "🤖 [系统启动] 正在唤醒 J.A.R.V.I.S. 核心逻辑...\n", "sys_color")
    chat_history.insert(tk.END, "🤖 [神经连结] Qwen2.5:14b 及语音引擎挂载完毕。\n\n", "sys_color")

    bottom_frame = tk.Frame(left_frame, bg="#0a0a0a")
    bottom_frame.pack(fill=tk.X)
    input_box = tk.Entry(bottom_frame, font=("微软雅黑", 12), bg="#1c1c1c", fg="white", insertbackground="white")
    input_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

    tk.Label(right_frame, text="📌 气象信标记录", font=("微软雅黑", 11, "bold"), bg="#1c1c1c", fg="white").pack(pady=10)
    history_list_frame = tk.Frame(right_frame, bg="#1c1c1c")
    history_list_frame.pack(fill=tk.BOTH, expand=True)

    def fetch_open_meteo(city):
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh"
            geo_res = requests.get(geo_url, timeout=5).json()
            if not geo_res.get("results"):
                return None, "全球气象卫星未定位到该目标。"
            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            weather_res = requests.get(weather_url, timeout=5).json()
            temp = weather_res["current_weather"]["temperature"]
            wind = weather_res["current_weather"]["windspeed"]
            return True, f"地表温度 {temp}°C，风速 {wind} km/h"
        except Exception as e:
            return None, f"卫星链路中断: {e}"

    def refresh_right_panel():
        for widget in history_list_frame.winfo_children():
            widget.destroy()
        for city in memory["starred"]:
            row_frame = tk.Frame(history_list_frame, bg="#1c1c1c")
            row_frame.pack(fill=tk.X, pady=2)
            tk.Button(row_frame, text=city, width=12, bg="#333333", fg="white", relief=tk.FLAT, command=lambda c=city: on_search(c)).pack(side=tk.LEFT, padx=5)
            tk.Button(row_frame, text="⭐", fg="gold", bg="#1c1c1c", relief=tk.FLAT, command=lambda c=city: toggle_star(c)).pack(side=tk.LEFT)
        if memory["recent"]:
            tk.Label(history_list_frame, text="--- 最近扫描 ---", bg="#1c1c1c", fg="#888888").pack(pady=10)
        for city in memory["recent"]:
            row_frame = tk.Frame(history_list_frame, bg="#1c1c1c")
            row_frame.pack(fill=tk.X, pady=2)
            tk.Button(row_frame, text=city, width=12, bg="#333333", fg="white", relief=tk.FLAT, command=lambda c=city: on_search(c)).pack(side=tk.LEFT, padx=5)
            tk.Button(row_frame, text="☆", fg="gray", bg="#1c1c1c", relief=tk.FLAT, command=lambda c=city: toggle_star(c)).pack(side=tk.LEFT)

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
        
        chat_history.insert(tk.END, f"\n👤 先生: 调取 【{city}】 的环境数据。\n", "user_color")
        win.update()

        try:
            success, weather_data = fetch_open_meteo(city)
            if not success:
                chat_history.insert(tk.END, f"🤖 J.A.R.V.I.S: {weather_data}\n", "normal_color")
            else:
                chat_history.insert(tk.END, f"🛰️ [卫星回传]: {weather_data}\n", "sys_color")
                win.update()
                
                prompt = f"""【最高系统强制指令】
身份设定：你是一个名为 J.A.R.V.I.S. (贾维斯) 的顶级私人人工智能管家。你的主人是“先生”(Sir)。
性格特征：极致理性、冷静、极其专业、带有纯正英式管家的克制与一丝高智商的优雅幽默。绝不使用“贴心”、“亲爱的”等谄媚词汇。
当前任务：向先生汇报环境数据，并提供精准的出行与着装建议。

定位城市：{city}
实时气象雷达数据：{weather_data}

执行规则：
1. 必须先进行数据分析，分析过程包裹在 <think> 和 </think> 标签内。
2. 思考完毕后，直接给出回复。回复必须以“先生，”开头。
3. 回复要极其简短干练、沉稳优雅，符合顶级 AI 管家的冷峻语调。全部使用中文。

示例输出：
<think>
温度偏低，风速较高。存在热量快速流失风险。建议穿着防风保暖衣物。
</think>
先生，目标区域气温较低且伴有强风。建议您出行时配备重型防风大衣。这种天气显然不适合在室外长时间逗留。
                """
                
                chat_history.insert(tk.END, f"🤖 J.A.R.V.I.S: \n", "normal_color")
                win.update()

                response_stream = ollama.chat(
                    model='qwen3.5:9b', 
                    messages=[{'role': 'user', 'content': prompt}], 
                    stream=True,
                    options={'temperature': 0.6} 
                )
                
                is_thinking = False 
                buffer = "" 
                final_speech = "" # 🌟 专门用一个箩筐，把真正要“念出来”的话攒起来
                
                for chunk in response_stream:
                    content_word = chunk['message'].get('content', '')
                    
                    if content_word:
                        buffer += content_word 
                        
                        if "<think>" in buffer:
                            chat_history.insert(tk.END, "╭─ [🧠 逻辑分析核心运转中] ─╮\n", "think_color")
                            is_thinking = True
                            buffer = buffer.replace("<think>", "") 
                            
                        if "</think>" in buffer:
                            chat_history.insert(tk.END, "\n╰─ [💡 分析报告生成完毕] ─╯\n\n", "think_color")
                            is_thinking = False
                            buffer = buffer.replace("</think>", "")
                            
                        if "<" in buffer and len(buffer) < 10:
                            continue 
                            
                        if buffer:
                            if is_thinking:
                                chat_history.insert(tk.END, buffer, "think_color")
                            else:
                                chat_history.insert(tk.END, buffer, "normal_color")
                                final_speech += buffer # 🌟 只有非思考的内容，才放入发声箩筐
                            buffer = "" 
                            
                    chat_history.see(tk.END)
                    win.update()
                
                chat_history.insert(tk.END, "\n\n")
                
                # 🌟 大功告成！让贾维斯开口说话！
                if final_speech:
                    jarvis_speak(final_speech)
                    
                update_memory_with_new_search(city)
                
        except Exception as e:
            chat_history.insert(tk.END, f"🤖 J.A.R.V.I.S: 先生，本地神经元网络连接异常。报错: {e}\n\n", "sys_color")
            
        input_box.delete(0, tk.END)
        chat_history.see(tk.END)

    win.bind('<Return>', lambda event: on_search())
    send_button = tk.Button(bottom_frame, text="执行指令", bg="#00e5ff", fg="black", font=("微软雅黑", 10, "bold"), command=on_search)
    send_button.pack(side=tk.LEFT)

    refresh_right_panel()
