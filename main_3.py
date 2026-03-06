# improved_chord_generator.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import webbrowser
import pygame.midi
import time
import threading
import ttkbootstrap as tb
from ttkbootstrap.constants import * 
from collections import OrderedDict
import cv2
from PIL import Image, ImageTk
import os
# import sys
# import pyautogui
# import json


# ---------- 定数定義 ---------
url = "github.com/aimlinux/Guitar_Sound"

main_theme = "solar" # 初期テーマを変数で管理
# テーマ候補（テーマ名はttkbootstrapのものを指定）
#🥇 cyborg（最もゲーム風）
#🥈 darkly（万能ダーク）
#🥉 superhero（コントラスト強）
#④ vapor（ネオン系）
#⑤ minty（爽やかライト）


# ---------- データ定義 ----------
DIATONIC_MAJOR = {
    'C': ['C','Dm','Em','F','G','Am','Bdim'],
    'G': ['G','Am','Bm','C','D','Em','F#dim'],
    'D': ['D','Em','F#m','G','A','Bm','C#dim'],
    'A': ['A','Bm','C#m','D','E','F#m','G#dim'],
    'E': ['E','F#m','G#m','A','B','C#m','D#dim'],
    'B': ['B','C#m','D#m','E','F#','G#m','A#dim'],
    'F#': ['F#','G#m','A#m','B','C#','D#m','E#dim'],
    'Gb': ['Gb','Abm','Bbm','Cb','Db','Ebm','Fdim'],
    'F': ['F','Gm','Am','Bb','C','Dm','Edim'],
    'Bb': ['Bb','Cm','Dm','Eb','F','Gm','Adim'],
    'Eb': ['Eb','Fm','Gm','Ab','Bb','Cm','Ddim'],
    'Ab': ['Ab','Bbm','Cm','Db','Eb','Fm','Gdim']
}

COMMON_PATTERNS = {
    'Pop': [
        ['I','V','vi','IV'],
        ['I','vi','IV','V'],
        ['vi','IV','I','V']
    ],
    'Rock': [
        ['I','IV','V','IV'],
        ['I','V','I','V']
    ],
    'Ballad': [ 
        ['I','vi','IV','V'],
        ['I','V','vi','IV'] 
    ],
    'Blues': [
        ['I','IV','I','V'],
        ['I','I','IV','I','V','IV','I','V']
    ]
}

CHORD_SHAPES = {
    'C': 'x32010',
    'G': '320003',
    'Am': 'x02210',
    'F': '133211',
    'Dm': 'xx0231',
    'Em': '022000',
    'D': 'xx0232',
    'E': '022100',
    'A': 'x02220',
    'Bm': 'x24432',
    'F#m': '244222',
    'B': 'x24442',
    'Bb': 'x13331'
}

ROMAN_TO_INDEX = {'I':0,'ii':1,'II':1,'iii':2,'III':2,'IV':3,'V':4,'vi':5,'VI':5,'vii°':6,'VII':6}

# midi note mapping for 4th octave
NOTE_TO_MIDI = {
    'C': 60, 'C#': 61, 'Db': 61,
    'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66,
    'G': 67, 'G#': 68, 'Ab': 68,
    'A': 69, 'A#': 70, 'Bb': 70,
    'B': 71
}

# ---------- ロジック ----------
def roman_to_chord(roman, key):
    """
    シンプルにローマ数字をDIATONIC_MAJORの対応するコードに変換する。
    小文字はマイナーを示す（ただしスケールの指定に従う）。
    '7' サフィックスがあれば簡易的に7thを追加（テンションは考慮せず表記のみ）。
    """
    roman_in = roman
    roman = roman.replace("°", "")
    add7 = False
    if roman.endswith('7'):
        add7 = True
        roman = roman[:-1]

    idx = ROMAN_TO_INDEX.get(roman, 0)
    chords = DIATONIC_MAJOR.get(key, DIATONIC_MAJOR['C'])
    base = chords[idx]
    if add7:
        # 簡易: メジャーなら7（maj7ではなくdom7表記は行わない）を付加、マイナーはm7
        if 'm' in base:
            return base + '7'  # Em -> Em7
        else:
            return base + '7'
    return base

def generate_progression(key, style, bars=4):
    patterns = COMMON_PATTERNS.get(style, COMMON_PATTERNS['Pop'])
    pattern = random.choice(patterns)
    prog = []
    i = 0
    while len(prog) < bars:
        prog.append(roman_to_chord(pattern[i % len(pattern)], key))
        i += 1 
    return prog

def get_shape(chord):
    return CHORD_SHAPES.get(chord, "N/A")

def parse_chord_name(chord_name):
    """
    ルートとタイプを分離。例: 'F#m7' -> ('F#','m7')
    """
    if len(chord_name) >= 2 and chord_name[1] in ['#', 'b']:
        root = chord_name[:2]
        chord_type = chord_name[2:]
    else:
        root = chord_name[0]
        chord_type = chord_name[1:]
    return root, chord_type

def chord_to_midi_notes(chord_name, octave_offset=0):
    """
    より柔軟な変換。
    - メジャー: 0, +4, +7
    - マイナー: 0, +3, +7
    - 7th (dominant/maj/min を簡易): 0,+4,+7,+10 (4音で演奏)
    octave_offset: ±12 per octave
    """
    root, ctype = parse_chord_name(chord_name)
    root_note = NOTE_TO_MIDI.get(root, 60) + octave_offset
    notes = []
    if 'm' in ctype and 'maj' not in ctype and '7' not in ctype:
        notes = [root_note, root_note+3, root_note+7]
    elif '7' in ctype:
        # simplistic: include 7th (dominant/minor/maj not fully distinguished)
        if 'maj' in ctype or 'M' in ctype:
            # maj7 -> 0,4,7,11
            notes = [root_note, root_note+4, root_note+7, root_note+11]
        elif 'm' in ctype:
            # m7 -> 0,3,7,10
            notes = [root_note, root_note+3, root_note+7, root_note+10]
        else:
            # dominant 7
            notes = [root_note, root_note+4, root_note+7, root_note+10]
    else:
        notes = [root_note, root_note+4, root_note+7]
    # ensure in reasonable midi range
    notes = [max(0, min(127, n)) for n in notes]
    return notes

# ---------- MIDI ハンドリング（シングルトン風） ----------
class MidiManager:
    def __init__(self):
        self.initialized = False
        self.output = None
        self.device_id = None
        self.lock = threading.Lock()

    def init(self):
        if not self.initialized:
            try:
                pygame.midi.init()
                self.initialized = True
            except Exception as e:
                print("MIDI init error:", e)
                self.initialized = False

    def list_devices(self):
        self.init()
        devs = []
        try:
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                interf, name, is_input, is_output, opened = info
                name = name.decode('utf-8') if isinstance(name, bytes) else str(name)
                devs.append((i, name, bool(is_output)))
        except Exception as e:
            print("Device listing error:", e)
        return devs

    def open_output(self, device_id):
        self.init()
        with self.lock:
            try:
                if self.output:
                    try:
                        self.output.close()
                    except:
                        pass
                self.output = pygame.midi.Output(device_id)
                self.device_id = device_id
                return True
            except Exception as e: 
                print("open_output error:", e)
                self.output = None
                return False

    def note_on(self, note, vel=100):
        with self.lock:
            if self.output:
                try:
                    self.output.note_on(int(note), int(vel))
                except:
                    pass

    def note_off(self, note, vel=100):
        with self.lock:
            if self.output:
                try:
                    self.output.note_off(int(note), int(vel))
                except: 
                    pass

    def close(self):
        with self.lock:
            try:
                if self.output:
                    self.output.close()
                    self.output = None
            except:
                pass
            try:
                if self.initialized:
                    pygame.midi.quit()
                    self.initialized = False
            except:
                pass

midi = MidiManager()


# ---------- タイトル画面 ----------
class TitleScreen:
    def __init__(self, root, start_callback):
        self.root = root
        self.start_callback = start_callback
        # テーマ変更に必要
        self.theme_var = tk.StringVar(value=self.root.style.theme.name) # テーマ管理用（TkinterのStringVarでリアクティブに）


        self.frame = tb.Frame(root)
        self.frame.pack(fill="both", expand=True)

        # ===== 動画設定 =====
        BASE_DIR = os.path.dirname(__file__)
        VIDEO_PATH = os.path.join(BASE_DIR, "video.mp4")

        self.cap = cv2.VideoCapture(VIDEO_PATH)

        self.video_label = tk.Label(self.frame)
        self.video_label.place(x=0, y=0, relwidth=1, relheight=1)

        # 動画再生開始
        self.update_frame()

        # ===== タイトルテキスト =====
        title = tb.Label(
            self.frame,
            text="🎸コードジェネレーター🎸",
            font=("Segoe UI", 50, "bold"),
            bootstyle="light"
        )
        title.place(relx=0.5, rely=0.3, anchor="center")

        subtitle = tb.Label(
            self.frame,
            text="美しい進行を作成",
            font=("Segoe UI", 30),
            bootstyle="secondary"
        )
        subtitle.place(relx=0.5, rely=0.4, anchor="center")

        # startボタン
        start_btn = tb.Button(
            self.frame,
            text="スタート",
            bootstyle="success",
            width=30,
            command=self.start
        )
        start_btn.place(relx=0.5, rely=0.6, anchor="center")

        # optionsボタン
        option_btn = tb.Button(
            self.frame,
            text="オプション",
            bootstyle="info",
            width=30,
            command=self.open_options
        )
        option_btn.place(relx=0.5, rely=0.7, anchor="center")

        # downloadボタン
        download_btn = tb.Button(
            self.frame,
            text="GitHub",
            bootstyle="secondary",
            width=30,
            command=self.download_program
        )
        download_btn.place(relx=0.5, rely=0.8, anchor="center")

        # Exitボタンも追加（タイトル画面からの退出用）
        exit_btn = tb.Button(
            self.frame,
            text="終わる",
            bootstyle="danger",
            width=30,
            command=self.exit
        )
        exit_btn.place(relx=0.5, rely=0.9, anchor="center")

    def update_frame(self):
        if not self.cap.isOpened():
            return

        ret, frame = self.cap.read()

        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            w = self.root.winfo_width()
            h = self.root.winfo_height()
            frame = cv2.resize(frame, (w, h))

            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(30, self.update_frame)

    # ----スタートボタンを押したときの処理----
    def start(self):
        self.cap.release()
        self.frame.destroy()
        self.start_callback()

    #----オプションボタンを押したときの処理----
    def open_options(self):
        """
        オプション設定ウィンドウ
        """
        option_win = tb.Toplevel(self.root)
        option_win.title("Options")
        option_win.geometry("800x600")
        option_win.grab_set()

        frame = tb.Frame(option_win, padding=20)
        frame.pack(fill="both", expand=True)

        tb.Label(
            frame,
            text="⚙オプション⚙",
            font=("Segoe UI", 18, "bold"),
            bootstyle="info"
        ).pack(pady=10)

        # ===== サンプル設定 =====
        tb.Label(frame, text="（ここに設定項目を追加できます）").pack(pady=10)

        # 例：BGM音量（ダミー）
        tb.Label(frame, text="BGM Volume").pack(anchor="w", pady=(10, 0))
        volume_var = tk.DoubleVar(value=0.5)
        tb.Scale(
            frame,
            from_=0,
            to=1,
            orient="horizontal",
            variable=volume_var,
            bootstyle="info"
        ).pack(fill="x", pady=5)

        # =============================
        # 🎨 テーマ変更
        # =============================
        tb.Label(frame, text="UI Theme").pack(anchor="w", pady=(15, 0))

        themes = self.root.style.theme_names()

        theme_combo = tb.Combobox(
            frame,
            values=themes,
            textvariable=self.theme_var,
            state="readonly",
            bootstyle="info"
        )
        theme_combo.pack(fill="x", pady=5)

        def on_theme_change(event):
            self.change_theme(self.theme_var.get())

        theme_combo.bind("<<ComboboxSelected>>", on_theme_change)


        tb.Button(
            frame,
            text="Close",
            bootstyle="secondary",
            command=option_win.destroy
        ).pack(pady=20)



    #----ダウンロードボタンを押したときの処理----
    def download_program(self):
        webbrowser.open(url)

    #----Exitボタンを押したときの処理----
    def exit(self):
        self.show_exit_dialog()


    def show_exit_dialog(self):

        # 🔥 オーバーレイ（背景暗くする）
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}")
        overlay.configure(bg="black")
        overlay.attributes("-alpha", 0.0)
        overlay.lift()
        overlay.grab_set()

        # フェードイン（暗転）
        def fade_overlay(alpha=0):
            if alpha <= 0.5:
                overlay.attributes("-alpha", alpha)
                overlay.after(20, lambda: fade_overlay(alpha + 0.05))

        fade_overlay()

        # 🔥 ダイアログ本体
        dialog = tb.Frame(overlay, padding=30, bootstyle="dark")
        dialog.place(relx=0.5, rely=0.5, anchor="center")
        dialog.attributes = overlay.attributes  # 透明度共有

        # サウンド再生
        try:
            pygame.mixer.Sound("confirm.wav").play()
        except:
            pass

        # メッセージ
        icon = tb.Label(dialog, text="⚠", font=("Segoe UI", 50), bootstyle="warning")
        icon.pack(pady=10)

        msg = tb.Label(dialog, text="ゲームを終了しますか？", font=("Segoe UI", 16))
        msg.pack(pady=10)

        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=10)

        # 最初は非表示
        btn_frame.pack_forget()

        def confirm():
            # self.play_flag.clear()
            # midi.close()
            # overlay.destroy()
            self.root.destroy()
            print("")
            print("-------- Exit App --------")
            print("")

        def cancel():
            overlay.destroy()

        exit_btn = tb.Button(btn_frame, text="Exit", bootstyle="danger", width=12, command=confirm)
        cancel_btn = tb.Button(btn_frame, text="Cancel", bootstyle="success", width=12, command=cancel)

        cancel_btn.pack(side="left", padx=10)
        exit_btn.pack(side="left", padx=10)

        # 🔥 ボタン遅れて出現
        def show_buttons():
            btn_frame.pack(pady=20)

        overlay.after(400, show_buttons)

    def change_theme(self, theme_name):
        """
        テーマをリアルタイム変更
        """
        try:
            self.root.style.theme_use(theme_name)
        except Exception as e:
            print("テーマ変更失敗:", e)



# ---------- GUI ----------
class ChordApp:
    def __init__(self, root, start_main): 
        self.root = root
        self.start_main = start_main  # ★超重要
        self.play_thread = None
        self.play_flag = threading.Event()
        self.build_ui()
        self.populate_midi_devices()

    def build_ui(self):
        # title
        title = tb.Label(self.root, text="🎸 ギターコードジェネレーター 🎸", font=("Segoe UI", 18, "bold"), bootstyle="info")
        title.pack(pady=12)

        control_frame = tb.Frame(self.root)
        control_frame.pack(pady=6, fill='x', padx=12)

        tb.Label(control_frame, text="キー：", font=("Segoe UI", 11)).grid(row=0, column=0, sticky='w', padx=4)
        self.key_var = tk.StringVar(value="C")
        self.key_menu = tb.Combobox(control_frame, textvariable=self.key_var, values=list(DIATONIC_MAJOR.keys()), width=6, state="readonly", bootstyle="info")
        self.key_menu.grid(row=0, column=1, padx=6)

        tb.Label(control_frame, text="スタイル：", font=("Segoe UI", 11)).grid(row=0, column=2, sticky='w', padx=4)
        self.style_var = tk.StringVar(value="Pop")
        self.style_menu = tb.Combobox(control_frame, textvariable=self.style_var, values=list(COMMON_PATTERNS.keys()), width=10, state="readonly", bootstyle="info")
        self.style_menu.grid(row=0, column=3, padx=6)

        tb.Label(control_frame, text="コード数：", font=("Segoe UI", 11)).grid(row=0, column=4, sticky='w', padx=4)
        self.bars_var = tk.IntVar(value=4)
        self.bars_spin = tb.Spinbox(control_frame, from_=1, to=16, textvariable=self.bars_var, width=5)
        self.bars_spin.grid(row=0, column=5, padx=6)

        tb.Label(control_frame, text="テンポ：", font=("Segoe UI", 11)).grid(row=1, column=0, sticky='w', padx=4, pady=6)
        self.tempo_var = tk.IntVar(value=90)
        self.tempo_slider = tb.Scale(control_frame, from_=40, to=200, orient='horizontal', bootstyle="info", variable=self.tempo_var, length=220)
        self.tempo_slider.grid(row=1, column=1, columnspan=3, sticky='w', padx=6)

        tb.Label(control_frame, text="MIDI出力デバイス:", font=("Segoe UI", 11)).grid(row=1, column=4, sticky='w', padx=4)
        self.midi_var = tk.StringVar(value="(Auto)")
        self.midi_menu = tb.Combobox(control_frame, textvariable=self.midi_var, values=[], width=24, state="readonly", bootstyle="info")
        self.midi_menu.grid(row=1, column=5, padx=6)

        # GitHubに飛ぶボタン
        self.github_btn = tb.Button(
            control_frame, 
            text="GitHub", 
            bootstyle="info", 
            width=20, 
            padding=(20, 14), 
            command=self.download_program)
        self.github_btn.grid(row=0, column=6, rowspan=2, padx=12)
        

        # タイトル画面に戻るボタン
        self.back_btn = tb.Button(
            control_frame, 
            text="タイトル画面に戻る", 
            bootstyle="success", 
            width=20, 
            padding=(20, 14), 
            command=self.back_to_title)
        self.back_btn.grid(row=0, column=7, rowspan=2, padx=12)

        # output frame
        output_frame = tb.Labelframe(self.root, text="生成されたコード進行", bootstyle="secondary")
        output_frame.pack(pady=8, fill="both", padx=12, expand=True)

        self.output_text = tk.Text(output_frame, width=80, height=10, wrap="word", font=("Consolas", 11), bg="#111", fg="#E8E8E8", relief="flat")
        self.output_text.pack(padx=8, pady=8, fill='both', expand=True)

        # bottom buttons and chord buttons area
        bottom_frame = tb.Frame(self.root)
        bottom_frame.pack(pady=8, fill='x', padx=12)

        self.generate_btn = tb.Button(bottom_frame, text="コードを生成する", bootstyle="success-outline", command=self.on_generate)
        self.generate_btn.pack(side='left', padx=6)

        self.save_btn = tb.Button(bottom_frame, text="進行を保存", bootstyle="secondary-outline", command=self.on_save)
        self.save_btn.pack(side='left', padx=6)

        self.play_btn = tb.Button(bottom_frame, text="進行を再生", bootstyle="info", command=self.on_play)
        self.play_btn.pack(side='left', padx=6)

        self.stop_btn = tb.Button(bottom_frame, text="止める", bootstyle="danger", command=self.on_stop)
        self.stop_btn.pack(side='left', padx=6)

        # options
        options_frame = tb.Frame(self.root)
        options_frame.pack(pady=6, fill='x', padx=12)
        self.play_style_var = tk.StringVar(value="Block")
        tb.Radiobutton(options_frame, text="ストローク", variable=self.play_style_var, value="Block", bootstyle="info").pack(side='left', padx=6)
        tb.Radiobutton(options_frame, text="アルペジオ", variable=self.play_style_var, value="Arp", bootstyle="info").pack(side='left', padx=6)

        self.loop_var = tk.BooleanVar(value=False)
        tb.Checkbutton(options_frame, text="Loop", variable=self.loop_var, bootstyle="success").pack(side='left', padx=8)

        # chord buttons area
        self.chord_buttons_frame = tb.Frame(self.root)
        self.chord_buttons_frame.pack(pady=8, fill='x', padx=12)

        # footer
        footer = tb.Label(self.root, text="Created by KAZUMA KOHARA", font=("Segoe UI", 10), bootstyle="secondary")
        footer.pack(side="bottom", pady=6)

    def populate_midi_devices(self):
        devs = midi.list_devices()
        out_devs = [f"{i}: {name}" for (i, name, is_out) in devs if is_out]
        if not out_devs:
            out_devs = ["(No MIDI output detected)"]
        self.midi_menu.configure(values=["(Auto)"] + out_devs)
        # keep default
        if out_devs:
            self.midi_menu.set("(Auto)")

    def on_generate(self):
        for w in self.chord_buttons_frame.winfo_children():
            w.destroy()

        key = self.key_var.get()
        style = self.style_var.get()
        bars = self.bars_var.get()
        progression = generate_progression(key, style, bars)
        result = f"Key: {key}    Style: {style}    Bars: {bars}\n\nProgression: | " + " | ".join(progression) + " |\n\n"
        for chord in progression:
            result += f"{chord:6s} → {get_shape(chord)}\n"

        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, result)

        # create chord quick-play buttons
        for chord in progression:
            btn = tb.Button(self.chord_buttons_frame, text=chord, width=8, bootstyle="success-outline",
                            command=lambda c=chord: threading.Thread(target=self.safe_play_chord, args=(c,)).start())
            btn.pack(side="left", padx=6, pady=4)

        # store current progression
        self.current_progression = progression

    def safe_play_chord(self, chord):
        """
        単一コードを安全に再生（非同期スレッド上）
        """
        try:
            # try auto open midi device if not opened
            self.ensure_midi_open()
            notes = chord_to_midi_notes(chord)
            for n in notes:
                midi.note_on(n, 100)
            time.sleep(0.8)
            for n in notes:
                midi.note_off(n, 100)
        except Exception as e:
            print("play error:", e)

    def ensure_midi_open(self):
        # MIDIデバイスを一度だけ開く。
        # 既に開いている場合は再度開かない。
        if midi.output is not None:
            return  # already opened
        
        self.midi_choice = self.midi_var.get()

        devs = midi.list_devices()
        outputs = [i for (i, name, is_out) in devs if is_out]

        if not outputs:
            return
        
        if self.midi_choice == "(Auto)":
            # try device 0 if exists
            devs = midi.list_devices()
            outputs = [i for (i, name, is_out) in devs if is_out]
            if outputs:
                midi.open_output(outputs[0])
        else:
            try:
                dev_id = int(self.midi_choice.split(":")[0])
                midi.open_output(dev_id)
            except Exception as e:
                print("cannot open selected device:", e)
                # fallback to auto
                devs = midi.list_devices()
                outputs = [i for (i, name, is_out) in devs if is_out]
                if outputs:
                    midi.open_output(outputs[0])

    def on_play(self):
        # start play thread
        if getattr(self, 'current_progression', None) is None:
            messagebox.showinfo("Info", "まずGenerate Progressionで進行を生成してください。")
            return
        if self.play_thread and self.play_thread.is_alive():
            messagebox.showinfo("Info", "既に再生中です。")
            return
        self.play_flag.set()
        self.play_thread = threading.Thread(target=self._loop, daemon=True)
        self.play_thread.start()

    def on_stop(self):
        self.play_flag.clear()
        # midi cleanup won't be forced here; notes turned off in thread
        time.sleep(0.05)

    def _loop(self):
        # open midi device
        try:
            self.ensure_midi_open()
        except:
            pass
        tempo = self.tempo_var.get()
        beat_length = 60.0 / tempo  # 1 beat (quarter note) in seconds

        progression = self.current_progression[:]
        play_style = self.play_style_var.get()
        loop = self.loop_var.get()

        try:
            while self.play_flag.is_set():
                for chord in progression:
                    if not self.play_flag.is_set():
                        break
                    notes = chord_to_midi_notes(chord, octave_offset=0)
                    if play_style == "Block":
                        # play all notes together for a duration of 2 beats (adjustable)
                        for n in notes:
                            midi.note_on(n, 100)
                        time.sleep(beat_length * 2)  # chord length = 2 beats
                        for n in notes:
                            midi.note_off(n, 100)
                    else:
                        # arpeggio: play notes sequentially across one bar (4 beats)
                        arpeggio_total = beat_length * 4
                        if notes:
                            step = arpeggio_total / len(notes)
                        else:
                            step = beat_length
                        for n in notes:
                            if not self.play_flag.is_set():
                                break
                            midi.note_on(n, 100)
                            time.sleep(step * 0.9)
                            midi.note_off(n, 100)
                        # short pause between chords
                        time.sleep(0.05)
                if not loop:
                    break
        finally:
            # ensure all notes off
            # attempt to turn off any lingering notes
            for n in range(0, 128):
                try:
                    midi.note_off(n, 0)
                except:
                    pass

    def on_save(self):
        if getattr(self, 'current_progression', None) is None:
            messagebox.showinfo("Info", "保存する進行がありません。まず生成してください。")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.output_text.get("1.0", tk.END))
            messagebox.showinfo("Saved", f"Saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"保存に失敗しました: {e}")

    def on_close(self):
        self.show_exit_dialog()
        # # stop thread and close midi
        # self.play_flag.clear()
        # if self.play_thread and self.play_thread.is_alive():
        #     self.play_thread.join(timeout=1.0)
        # midi.close()
        # self.root.destroy()


    def show_exit_dialog(self):

        # 🔥 オーバーレイ（背景暗くする）
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}")
        overlay.configure(bg="black")
        overlay.attributes("-alpha", 0.0)
        overlay.lift()
        overlay.grab_set()

        # フェードイン（暗転）
        def fade_overlay(alpha=0):
            if alpha <= 0.5:
                overlay.attributes("-alpha", alpha)
                overlay.after(20, lambda: fade_overlay(alpha + 0.05))

        fade_overlay()

        # 🔥 ダイアログ本体
        dialog = tb.Frame(overlay, padding=30, bootstyle="dark")
        dialog.place(relx=0.5, rely=0.5, anchor="center")
        dialog.attributes = overlay.attributes  # 透明度共有

        # サウンド再生
        try:
            pygame.mixer.Sound("confirm.wav").play()
        except:
            pass

        # メッセージ
        icon = tb.Label(dialog, text="⚠", font=("Segoe UI", 50), bootstyle="warning")
        icon.pack(pady=10)

        msg = tb.Label(dialog, text="ゲームを終了しますか？", font=("Segoe UI", 16))
        msg.pack(pady=10)

        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=10)

        # 最初は非表示
        btn_frame.pack_forget()

        def confirm():
            self.play_flag.clear()
            midi.close()
            overlay.destroy()
            self.root.destroy()
            print("")
            print("-------- Exit App --------")
            print("")

        def cancel():
            overlay.destroy()

        exit_btn = tb.Button(btn_frame, text="Exit", bootstyle="danger", width=12, command=confirm)
        cancel_btn = tb.Button(btn_frame, text="Cancel", bootstyle="success", width=12, command=cancel)

        cancel_btn.pack(side="left", padx=10)
        exit_btn.pack(side="left", padx=10)
        
        # 🔥 ボタン遅れて出現
        def show_buttons():
            btn_frame.pack(pady=20)

        overlay.after(400, show_buttons)


    def back_to_title(self):    
        if not messagebox.askyesno("確認", "タイトルに戻りますか？"):
            return

        # ===== 動画・音・スレッド停止 =====
        try:
            if hasattr(self, "play_flag"):
                self.play_flag.clear()
        except Exception:
            pass

        # ===== 画面破棄 =====
        if self.root.winfo_exists():
            for w in self.root.winfo_children():
                w.destroy()

        # ===== TitleScreen 再生成 =====
        TitleScreen(self.root, self.start_main)

    #----ダウンロードボタンを押したときの処理----
    def download_program(self):
        webbrowser.open(url)

def main():
    root = tb.Window(themename=main_theme) #初期テーマ
    root.title("Guitar Chord Progression Generator (Improved)")

    # 画面サイズ取得
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    #　画面の80%のサイズにウィンドウを設定
    window_width = int(screen_width * 0.8)
    window_height = int(screen_height * 0.8)

    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    #window最小サイズ設定
    root.minsize(800, 600)
    
    #サイズ変更可能にする
    root.resizable(True, True)


    # タイトル画面 → メイン画面切り替え
    def start_main():
        app = ChordApp(root, start_main)
        root.protocol("WM_DELETE_WINDOW", app.on_close)

    TitleScreen(root, start_main)

    root.mainloop()

if __name__ == "__main__":
    main() 


# やはりpythonでは限界を感じます
# もっとリッチなUIや安定したMIDI再生を求めるなら、C#のWPFやUnity、あるいはC++のQtなどのフレームワークを検討するのが良いかもしれません。
# ただ、Pythonでここまでできたのは個人的には満足しています。
# もし将来的に機能追加や改善をするなら、以下のようなアイデアがあります：

# - コード進行のカスタマイズ（ユーザーがコードを追加・編集できるようにする）
# - MIDIファイルへのエクスポート機能
# - より高度なコード理論のサポート（セカンダリードミナント、モーダルインターチェンジなど）
# - コードのボイシングやテンションの選択肢を増やす
# - UIの改善（コードの図示、リアルタイムでのコード変更など）
# - エラー処理の強化（MIDIデバイスの問題、ファイル保存の失敗などへの対応）
# などなど。 
# 今後もこのプロジェクトを成長させていくのが楽しみです！