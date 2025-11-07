import tkinter as tk
from tkinter import ttk
import random
import pygame.midi
import time

# ---------- データ定義 ----------

# ダイアトニックコード（メジャーキー）
DIATONIC_MAJOR = {
    'C': ['C','Dm','Em','F','G','Am','Bdim'],
    'G': ['G','Am','Bm','C','D','Em','F#dim'],
    'D': ['D','Em','F#m','G','A','Bm','C#dim'],
    'A': ['A','Bm','C#m','D','E','F#m','G#dim'],
    'E': ['E','F#m','G#m','A','B','C#m','D#dim'],
    'F': ['F','Gm','Am','Bb','C','Dm','Edim']
}

# よく使われるコード進行パターン
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
    ]
}

# コードフォーム（押さえ方）
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

# ---------- コード関連関数 ----------

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

# ---------- MIDI 再生関連 ----------

def chord_to_midi_notes(chord_name):
    # ルート音抽出
    root = chord_name[0]
    if len(chord_name) > 1 and chord_name[1] in ['#', 'b']:
        root = chord_name[:2]
        chord_type = chord_name[2:]
    else:
        chord_type = chord_name[1:]
    root_note = NOTE_TO_MIDI.get(root, 60)

    # major/minor 判定
    if 'm' in chord_type and 'maj' not in chord_type:
        return [root_note, root_note+3, root_note+7]  # minor triad
    else:
        return [root_note, root_note+4, root_note+7]  # major triad

def play_chord(chord_name):
    notes = chord_to_midi_notes(chord_name)
    pygame.midi.init()
    try:
        player = pygame.midi.Output(0)
        volume = 100
        for note in notes:
            player.note_on(note, volume)
        time.sleep(0.7)
        for note in notes:
            player.note_off(note, volume)
        del player
    except Exception as e:
        print("音を再生できません:", e)
    finally:
        pygame.midi.quit()

# ---------- GUI部分 ----------

root = tk.Tk()
root.title("🎸 ギターコード進行ジェネレータ（再生付き）")
root.geometry("550x500")
root.resizable(False, False)

title_label = tk.Label(root, text="🎸 ギターコード進行ジェネレータ🎸", font=("Meiryo", 16, "bold"))
title_label.pack(pady=10)

# 入力選択フレーム
frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="キー:").grid(row=0, column=0, padx=5)
key_var = tk.StringVar(value="C")
key_menu = ttk.Combobox(frame, textvariable=key_var, values=list(DIATONIC_MAJOR.keys()), width=5, state="readonly")
key_menu.grid(row=0, column=1, padx=5)

tk.Label(frame, text="スタイル:").grid(row=0, column=2, padx=5)
style_var = tk.StringVar(value="Pop")
style_menu = ttk.Combobox(frame, textvariable=style_var, values=list(COMMON_PATTERNS.keys()), width=8, state="readonly")
style_menu.grid(row=0, column=3, padx=5)

# 結果エリア
output_frame = tk.Frame(root)
output_frame.pack(pady=10)

output_text = tk.Text(output_frame, width=60, height=10, wrap="word", font=("Consolas", 11))
output_text.grid(row=0, column=0, padx=10)

# コードボタンエリア
chord_buttons_frame = tk.Frame(root)
chord_buttons_frame.pack(pady=10)

def on_generate():
    for widget in chord_buttons_frame.winfo_children():
        widget.destroy()

    key = key_var.get()
    style = style_var.get()
    progression = generate_progression(key, style)
    result = f"キー: {key}　スタイル: {style}\n\n進行: | " + " | ".join(progression) + " |\n\n"
    for chord in progression:
        result += f"{chord:4s} → {get_shape(chord)}\n"

    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, result)

    # コードボタン生成
    for chord in progression:
        btn = tk.Button(chord_buttons_frame, text=chord, width=8, height=2,
                        bg="#4CAF50", fg="white", font=("Meiryo", 11, "bold"),
                        command=lambda c=chord: play_chord(c))
        btn.pack(side="left", padx=5)

generate_button = tk.Button(root, text="🎶  コード進行を生成 🎶 ", font=("Meiryo", 12),
                            command=on_generate, bg="#4CAF50", fg="white")
generate_button.pack(pady=10)

root.mainloop()
