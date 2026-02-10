# improved_chord_generator_complete.py
import tkinter as tk
from tkinter import filedialog, messagebox
import random
import pygame.midi
import time
import threading
import ttkbootstrap as tb

# ===============================
# データ定義
# ===============================

DIATONIC_MAJOR = {
    'C':  ['C','Dm','Em','F','G','Am','Bdim'],
    'G':  ['G','Am','Bm','C','D','Em','F#dim'],
    'D':  ['D','Em','F#m','G','A','Bm','C#dim'],
    'A':  ['A','Bm','C#m','D','E','F#m','G#dim'],
    'E':  ['E','F#m','G#m','A','B','C#m','D#dim'],
    'F':  ['F','Gm','Am','Bb','C','Dm','Edim'],
    'Bb': ['Bb','Cm','Dm','Eb','F','Gm','Adim'],
    'Eb': ['Eb','Fm','Gm','Ab','Bb','Cm','Ddim'],
    'Ab': ['Ab','Bbm','Cm','Db','Eb','Fm','Gdim']
}

COMMON_PATTERNS = {
    'Pop': [
        ['I','V','vi','IV'],
        ['I','vi','IV','V']
    ],
    'Rock': [
        ['I','IV','V','IV'],
        ['I','V','I','V']
    ],
    'Ballad': [
        ['I','vi','IV','V']
    ],
    'Blues': [
        ['I','IV','I','V']
    ]
}

CHORD_SHAPES = {
    'C':'x32010','G':'320003','Am':'x02210','F':'133211',
    'Dm':'xx0231','Em':'022000','D':'xx0232','E':'022100',
    'A':'x02220','Bm':'x24432','Bb':'x13331'
}

ROMAN_TO_INDEX = {
    'I':0,'ii':1,'iii':2,'IV':3,'V':4,'vi':5,'vii':6,
    'II':1,'III':2,'VI':5,'VII':6
}

NOTE_TO_MIDI = {
    'C':60,'C#':61,'Db':61,'D':62,'D#':63,'Eb':63,
    'E':64,'F':65,'F#':66,'Gb':66,'G':67,'G#':68,
    'Ab':68,'A':69,'A#':70,'Bb':70,'B':71
}

# ===============================
# ロジック
# ===============================

def roman_to_chord(roman, key):
    roman = roman.replace('°','')
    add7 = roman.endswith('7')
    if add7:
        roman = roman[:-1]

    idx = ROMAN_TO_INDEX.get(roman, 0)
    base = DIATONIC_MAJOR[key][idx]
    return base + '7' if add7 else base

def generate_progression(key, style, bars):
    pattern = random.choice(COMMON_PATTERNS[style])
    return [roman_to_chord(pattern[i % len(pattern)], key) for i in range(bars)]

def chord_to_midi_notes(chord):
    root = chord[:2] if len(chord)>1 and chord[1] in '#b' else chord[0]
    ctype = chord[len(root):]
    base = NOTE_TO_MIDI.get(root, 60)

    if 'm' in ctype and '7' not in ctype:
        intervals = [0,3,7]
    elif '7' in ctype:
        intervals = [0,4,7,10] if 'm' not in ctype else [0,3,7,10]
    else:
        intervals = [0,4,7]

    return [base+i for i in intervals]

# ===============================
# MIDI 管理
# ===============================

class MidiManager:
    def __init__(self):
        pygame.midi.init()
        self.output = None

    def open_auto(self):
        for i in range(pygame.midi.get_count()):
            if pygame.midi.get_device_info(i)[3]:
                self.output = pygame.midi.Output(i)
                return True
        return False

    def play_chord(self, notes, length):
        for n in notes:
            self.output.note_on(n, 100)
        time.sleep(length)
        for n in notes:
            self.output.note_off(n, 100)

    def close(self):
        if self.output:
            self.output.close()
        pygame.midi.quit()

midi = MidiManager()

# ===============================
# GUI
# ===============================

class ChordApp:
    def __init__(self, root):
        self.root = root
        self.playing = False
        self.build_ui()

    def build_ui(self):
        self.root.title("Guitar Chord Progression Generator")
        self.root.geometry("900x650")

        tb.Label(self.root, text="Chord Progression Generator",
                 font=("Segoe UI",18,"bold")).pack(pady=10)

        frame = tb.Frame(self.root)
        frame.pack()

        self.key = tk.StringVar(value='C')
        self.style = tk.StringVar(value='Pop')
        self.bars = tk.IntVar(value=4)
        self.tempo = tk.IntVar(value=90)

        tb.Combobox(frame, textvariable=self.key,
                    values=list(DIATONIC_MAJOR.keys()), width=6).grid(row=0,column=0,padx=5)
        tb.Combobox(frame, textvariable=self.style,
                    values=list(COMMON_PATTERNS.keys()), width=10).grid(row=0,column=1,padx=5)
        tb.Spinbox(frame, from_=1, to=16, textvariable=self.bars, width=5).grid(row=0,column=2,padx=5)

        tb.Scale(frame, from_=40, to=200, variable=self.tempo,
                 length=200).grid(row=1,column=0,columnspan=3,pady=5)

        self.text = tk.Text(self.root, height=10, bg="#111", fg="white")
        self.text.pack(fill="both", padx=10, pady=10, expand=True)

        btn = tb.Frame(self.root)
        btn.pack()

        tb.Button(btn, text="Generate", command=self.generate).pack(side="left",padx=5)
        tb.Button(btn, text="Play", command=self.play).pack(side="left",padx=5)
        tb.Button(btn, text="Stop", command=self.stop).pack(side="left",padx=5)

    def generate(self):
        self.progression = generate_progression(
            self.key.get(), self.style.get(), self.bars.get()
        )
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, " | ".join(self.progression))

    def play(self):
        if self.playing or not hasattr(self, 'progression'):
            return
        self.playing = True
        midi.open_auto()

        def run():
            beat = 60/self.tempo.get()
            for chord in self.progression:
                if not self.playing:
                    break
                midi.play_chord(chord_to_midi_notes(chord), beat*2)
            self.playing = False

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self.playing = False

def main():
    root = tb.Window(themename="darkly")
    ChordApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
