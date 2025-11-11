import tkinter as tk
from tkinter import ttk
import random
import pygame.midi
import time
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ---------- データ定義 ----------

DIATONIC_MAJOR = {
    'C': ['C','Dm','Em','F','G','Am','Bdim'],
    'G': ['G','Am','Bm','C','D','Em','F#dim'],
    'D': ['D','Em','F#m','G','A','Bm','C#dim'],
    'A': ['A','Bm','C#m','D','E','F#m','G#dim'],
    'E': ['E','F#m','G#m','A','B','C#m','D#dim'],
    'F': ['F','Gm','Am','Bb','C','Dm','Edim']
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
    'F#m': '244222' 
}

ROMAN_TO_INDEX = {'I':0,'ii':1,'II':1,'iii':2,'III':2,'IV':3,'V':4,'vi':5,'VI':5,'vii°':6,'VII':6}

NOTE_TO_MIDI = {
    'C': 60, 'C#': 61, 'Db': 61,
    'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66,
    'G': 67, 'G#': 68, 'Ab': 68,
    'A': 69, 'A#': 70, 'Bb': 70,
    'B': 71
} 

# ---------- コード関連 ----------

def roman_to_chord(roman, key):
    roman = roman.replace("°", "")
    idx = ROMAN_TO_INDEX.get(roman, 0)
    chords = DIATONIC_MAJOR.get(key, DIATONIC_MAJOR['C'])
    return chords[idx]

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

# ---------- MIDI再生 ----------

def chord_to_midi_notes(chord_name):
    root = chord_name[0]
    if len(chord_name) > 1 and chord_name[1] in ['#', 'b']:
        root = chord_name[:2]
        chord_type = chord_name[2:]
    else:
        chord_type = chord_name[1:]
    root_note = NOTE_TO_MIDI.get(root, 60)

    if 'm' in chord_type and 'maj' not in chord_type:
        return [root_note, root_note+3, root_note+7]
    else:
        return [root_note, root_note+4, root_note+7]

def play_chord(chord_name):
    notes = chord_to_midi_notes(chord_name)
    pygame.midi.init()
    try:
        player = pygame.midi.Output(0)
        volume = 100
        for note in notes:
            player.note_on(note, volume)
        time.sleep(0.6)
        for note in notes:
            player.note_off(note, volume)
        del player
    except Exception as e:
        print("音を再生できません:", e)
    finally:
        pygame.midi.quit()

# ---------- GUI ----------

root = tb.Window(themename="darkly")
root.title(" Guitar Chord Progression Generator ")
root.geometry("800x700")
root.resizable(False, False)

# タイトル
title_label = tb.Label(
    root,
    text=" Guitar Chord Progression Generator ",
    font=("Segoe UI", 18, "bold"),
    bootstyle="info" 
)
title_label.pack(pady=15)

# 入力選択フレーム
frame = tb.Frame(root)
frame.pack(pady=10)

tb.Label(frame, text="Key:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=5)
key_var = tk.StringVar(value="C")
key_menu = tb.Combobox(frame, textvariable=key_var, values=list(DIATONIC_MAJOR.keys()), width=5, state="readonly", bootstyle="info")
key_menu.grid(row=0, column=1, padx=5)

tb.Label(frame, text="Style:", font=("Segoe UI", 12)).grid(row=0, column=2, padx=5)
style_var = tk.StringVar(value="Pop")
style_menu = tb.Combobox(frame, textvariable=style_var, values=list(COMMON_PATTERNS.keys()), width=8, state="readonly", bootstyle="info")
style_menu.grid(row=0, column=3, padx=5)

# 出力テキスト（枠付き）
output_frame = tb.Labelframe(root, text=" Generated Progression", bootstyle="secondary")
output_frame.pack(pady=10, fill="x", padx=15)

output_text = tk.Text(output_frame, width=65, height=10, wrap="word", font=("Consolas", 11), bg="#222", fg="#E8E8E8", relief="flat")
output_text.pack(padx=10, pady=5)

# コードボタンエリア
chord_buttons_frame = tb.Frame(root)
chord_buttons_frame.pack(pady=15)

def on_generate():
    for widget in chord_buttons_frame.winfo_children():
        widget.destroy()

    key = key_var.get()
    style = style_var.get()
    progression = generate_progression(key, style)
    result = f"Key: {key}  Style: {style}\n\nProgression: | " + " | ".join(progression) + " |\n\n"
    for chord in progression:
        result += f"{chord:4s} → {get_shape(chord)}\n"

    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, result)

    for chord in progression:
        btn = tb.Button(
            chord_buttons_frame,
            text=chord,
            width=8,
            bootstyle="success-outline",
            command=lambda c=chord: play_chord(c)
        )
        btn.pack(side="left", padx=8)

# 生成ボタン
generate_button = tb.Button(
    root,
    text="🎶 Generate Progression",
    bootstyle="info-outline",
    width=25,
    command=on_generate,
    padding=(10, 10),         # 横・縦方向の余白（px）
)
generate_button.pack(pady=20)

# クレジット
footer = tb.Label(
    root,
    text="Created by KAZUMA KOHARA",
    font=("Segoe UI", 18),
    bootstyle="secondary"
)
footer.pack(side="bottom", pady=8)
   
root.mainloop()
