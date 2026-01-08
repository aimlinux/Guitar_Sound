# improved_chord_generator_complete_fixed.py
"""
完成版・安定動作するギターコード進行ジェネレータ
"""

import json
import os
import random
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import pygame.midi
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ================== データ ==================
DIATONIC_MAJOR = {
    'C': ['C','Dm','Em','F','G','Am','Bdim'],
    'G': ['G','Am','Bm','C','D','Em','F#dim'],
    'D': ['D','Em','F#m','G','A','Bm','C#dim'],
    'A': ['A','Bm','C#m','D','E','F#m','G#dim'],
    'E': ['E','F#m','G#m','A','B','C#m','D#dim'],
    'F': ['F','Gm','Am','Bb','C','Dm','Edim'],
}

COMMON_PATTERNS = {
    'Pop': [['I','V','vi','IV'], ['I','vi','IV','V']],
    'Rock': [['I','IV','V','IV']],
    'Ballad': [['I','vi','IV','V']],
}

ROMAN_TO_INDEX = {'I':0,'ii':1,'iii':2,'IV':3,'V':4,'vi':5,'vii°':6}

NOTE_TO_MIDI = {
    'C':60,'C#':61,'Db':61,'D':62,'D#':63,'Eb':63,
    'E':64,'F':65,'F#':66,'Gb':66,'G':67,'G#':68,
    'Ab':68,'A':69,'Bb':70,'B':71
}

SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.chord_gen_settings.json')

# ================== 設定 ==================
def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE,'r',encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_settings(d):
    try:
        with open(SETTINGS_FILE,'w',encoding='utf-8') as f:
            json.dump(d,f,ensure_ascii=False,indent=2)
    except:
        pass

# ================== 音楽ロジック ==================
def roman_to_chord(roman, key):
    roman = roman.replace('°','')
    idx = ROMAN_TO_INDEX.get(roman,0)
    return DIATONIC_MAJOR[key][idx]

def generate_progression(key, style, bars):
    pat = random.choice(COMMON_PATTERNS[style])
    return [roman_to_chord(pat[i % len(pat)], key) for i in range(bars)]

def parse_chord(ch):
    if len(ch) > 1 and ch[1] in '#b':
        return ch[:2], ch[2:]
    return ch[0], ch[1:]

def chord_to_notes(chord, octave, inversion):
    root, ctype = parse_chord(chord)
    base = NOTE_TO_MIDI[root] + octave * 12
    notes = [base, base+4, base+7] if 'm' not in ctype else [base, base+3, base+7]
    for _ in range(inversion):
        notes.append(notes.pop(0) + 12)
    return notes

# ================== MIDI ==================
class MidiManager:
    def __init__(self):
        pygame.midi.init()
        self.out = None

    def open_auto(self):
        for i in range(pygame.midi.get_count()):
            if pygame.midi.get_device_info(i)[3]:
                self.out = pygame.midi.Output(i)
                return

    def note_on(self, n, v):
        if self.out:
            self.out.note_on(int(n), int(v))

    def note_off(self, n):
        if self.out:
            self.out.note_off(int(n), 0)

    def all_off(self):
        if self.out:
            for n in range(128):
                self.out.note_off(n,0)

    def close(self):
        self.all_off()
        if self.out:
            self.out.close()
        pygame.midi.quit()

MIDI = MidiManager()

# ================== UI ==================
class ChordApp:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.progression = []
        self.play_flag = threading.Event()
        self.build_ui()
        MIDI.open_auto()

    def build_ui(self):
        self.root.title("Guitar Chord Generator")
        self.root.geometry("900x600")

        f = tb.Frame(self.root)
        f.pack(padx=10,pady=10)

        self.key = tk.StringVar(value='C')
        self.style = tk.StringVar(value='Pop')
        self.bars = tk.IntVar(value=4)
        self.tempo = tk.IntVar(value=90)
        self.play_style = tk.StringVar(value='Block')
        self.loop = tk.BooleanVar(value=False)
        self.oct = tk.IntVar(value=0)
        self.inv = tk.IntVar(value=0)
        self.vel = tk.IntVar(value=100)
        self.human = tk.IntVar(value=20)

        tb.Combobox(f, values=list(DIATONIC_MAJOR), textvariable=self.key).grid(row=0,column=1)
        tb.Combobox(f, values=list(COMMON_PATTERNS), textvariable=self.style).grid(row=0,column=3)
        tb.Spinbox(f, from_=1,to=16,textvariable=self.bars,width=5).grid(row=0,column=5)

        tb.Button(f,text="Generate",command=self.generate).grid(row=1,column=0,pady=6)
        tb.Button(f,text="Play",command=self.play).grid(row=1,column=1)
        tb.Button(f,text="Stop",command=self.stop).grid(row=1,column=2)

        self.text = tk.Text(self.root,height=8,font=('Consolas',12))
        self.text.pack(fill='x',padx=10,pady=10)

        self.btn_frame = tb.Frame(self.root)
        self.btn_frame.pack(pady=6)

    def generate(self):
        self.progression = generate_progression(self.key.get(), self.style.get(), self.bars.get())
        self.text.delete('1.0','end')
        self.text.insert('end',' | '.join(self.progression))
        for w in self.btn_frame.winfo_children():
            w.destroy()
        for c in self.progression:
            tb.Button(self.btn_frame,text=c,
                      command=lambda x=c:self.play_chord(x)).pack(side='left',padx=4)

    def play_chord(self, chord):
        notes = chord_to_notes(chord, self.oct.get(), self.inv.get())
        for n in notes:
            MIDI.note_on(n, self.vel.get())
        time.sleep(0.8)
        for n in notes:
            MIDI.note_off(n)

    def play(self):
        if not self.progression:
            return
        self.play_flag.set()
        threading.Thread(target=self.play_loop,daemon=True).start()

    def play_loop(self):
        beat = 60 / self.tempo.get()
        while self.play_flag.is_set():
            for c in self.progression:
                if not self.play_flag.is_set():
                    break
                notes = chord_to_notes(c,self.oct.get(),self.inv.get())
                for n in notes:
                    MIDI.note_on(n,self.vel.get())
                time.sleep(beat*4)
                for n in notes:
                    MIDI.note_off(n)
            if not self.loop.get():
                break
        MIDI.all_off()

    def stop(self):
        self.play_flag.clear()
        MIDI.all_off()

def main():
    root = tb.Window(themename='vapor')
    app = ChordApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (MIDI.close(), root.destroy()))
    root.mainloop()

if __name__ == '__main__':
    main()
