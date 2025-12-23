# improved_chord_generator_complete.py
"""
おしゃれで完成版のギターコード進行ジェネレータ
- ttkbootstrap を使ったモダンUI
- MIDI 出力（pygame.midi）で進行を再生
- コードのインバージョン、オクターブ、ベロシティ、ヒューマナイズ対応
- 再生中のコードハイライト、ループ、保存、設定の永続化
- エラーハンドリングとデバイス自動選択

使い方:
    pip install pygame ttkbootstrap
    python improved_chord_generator_complete.py
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

# ------------------ データ ------------------
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
    'Pop': [ ['I','V','vi','IV'], ['I','vi','IV','V'], ['vi','IV','I','V'] ],
    'Rock': [ ['I','IV','V','IV'], ['I','V','I','V'] ],
    'Ballad': [ ['I','vi','IV','V'], ['I','V','vi','IV'] ],
    'Blues': [ ['I','IV','I','V'], ['I','I','IV','I','V','IV','I','V'] ]
}

CHORD_SHAPES = {
    'C': 'x32010', 'G': '320003', 'Am': 'x02210', 'F': '133211',
    'Dm': 'xx0231', 'Em': '022000', 'D': 'xx0232', 'E': '022100',
    'A': 'x02220', 'Bm': 'x24432', 'F#m': '244222', 'B': 'x24442', 'Bb': 'x13331'
}

ROMAN_TO_INDEX = {'I':0,'ii':1,'II':1,'iii':2,'III':2,'IV':3,'V':4,'vi':5,'VI':5,'vii°':6,'VII':6}

NOTE_TO_MIDI = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68, 'Ab': 68,
    'A': 69, 'A#': 70, 'Bb': 70, 'B': 71
}

SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.chord_gen_settings.json')

# ------------------ ユーティリティ ------------------

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_settings(d):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ------------------ 音楽ロジック ------------------

def roman_to_chord(roman, key):
    add7 = False
    roman_in = roman
    roman = roman.replace('°','')
    if roman.endswith('7'):
        add7 = True
        roman = roman[:-1]
    idx = ROMAN_TO_INDEX.get(roman, 0)
    chords = DIATONIC_MAJOR.get(key, DIATONIC_MAJOR['C'])
    base = chords[idx]
    if add7:
        if 'm' in base:
            return base + '7'
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


def parse_chord_name(chord_name):
    if len(chord_name) >= 2 and chord_name[1] in ('#','b'):
        root = chord_name[:2]
        chord_type = chord_name[2:]
    else:
        root = chord_name[0]
        chord_type = chord_name[1:]
    return root, chord_type


def chord_to_midi_notes(chord_name, octave=0, inversion=0):
    root, ctype = parse_chord_name(chord_name)
    root_note = NOTE_TO_MIDI.get(root, 60) + octave
    notes = []
    # triads
    if 'm' in ctype and 'maj' not in ctype and '7' not in ctype:
        notes = [root_note, root_note+3, root_note+7]
    elif '7' in ctype:
        if 'maj' in ctype or 'M' in ctype:
            notes = [root_note, root_note+4, root_note+7, root_note+11]
        elif 'm' in ctype:
            notes = [root_note, root_note+3, root_note+7, root_note+10]
        else:
            notes = [root_note, root_note+4, root_note+7, root_note+10]
    else:
        notes = [root_note, root_note+4, root_note+7]
    # apply inversion: rotate and shift up an octave if needed
    for _ in range(inversion):
        if notes:
            note = notes.pop(0) + 12
            notes.append(note)
    # clamp
    notes = [max(0, min(127, n)) for n in notes]
    return notes


# ------------------ MIDI 管理 ------------------
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
                print('MIDI init error:', e)
                self.initialized = False

    def list_devices(self):
        self.init()
        devs = []
        try:
            count = pygame.midi.get_count()
            for i in range(count):
                info = pygame.midi.get_device_info(i)
                interf, name, is_input, is_output, opened = info
                name = name.decode('utf-8') if isinstance(name, bytes) else str(name)
                devs.append((i, name, bool(is_output)))
        except Exception as e:
            print('Device listing error:', e)
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
                print('open_output error:', e)
                self.output = None
                return False

    def note_on(self, note, vel=100):
        with self.lock:
            if self.output:
                try:
                    self.output.note_on(int(note), int(vel))
                except Exception:
                    pass

    def note_off(self, note, vel=0):
        with self.lock:
            if self.output:
                try:
                    self.output.note_off(int(note), int(vel))
                except Exception:
                    pass

    def all_notes_off(self):
        with self.lock:
            if self.output:
                for n in range(128):
                    try:
                        self.output.note_off(n, 0)
                    except:
                        pass

    def close(self):
        with self.lock:
            try:
                if self.output:
                    try:
                        self.output.close()
                    except:
                        pass
                    self.output = None
            except:
                pass
            try:
                if self.initialized:
                    pygame.midi.quit()
                    self.initialized = False
            except:
                pass

MIDI = MidiManager()

# ------------------ UI & アプリ ------------------
class ChordApp:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.current_progression = []
        self.play_thread = None
        self.play_flag = threading.Event()
        self.build_ui()
        self.populate_midi_devices()
        self.restore_settings()

    def build_ui(self):
        root = self.root
        root.title('Guitar Chord Progression Generator — Stylish')
        root.geometry('980x700')

        header = tb.Frame(root)
        header.pack(fill='x', padx=12, pady=8)

        tb.Label(header, text='Guitar Chord Progression Generator', font=('Segoe UI', 18, 'bold'), bootstyle='primary').pack(side='left')
        tb.Label(header, text='by KAZUMA KOHARA', font=('Segoe UI', 10), bootstyle='secondary').pack(side='right')

        control = tb.Frame(root)
        control.pack(fill='x', padx=12, pady=6)

        tb.Label(control, text='Key:', font=('Segoe UI', 11)).grid(row=0, column=0, sticky='w', padx=4, pady=2)
        self.key_var = tk.StringVar(value='C')
        self.key_menu = tb.Combobox(control, textvariable=self.key_var, values=list(DIATONIC_MAJOR.keys()), width=7, state='readonly', bootstyle='info')
        self.key_menu.grid(row=0, column=1, padx=6, sticky='w')

        tb.Label(control, text='Style:', font=('Segoe UI', 11)).grid(row=0, column=2, sticky='w', padx=4)
        self.style_var = tk.StringVar(value='Pop')
        self.style_menu = tb.Combobox(control, textvariable=self.style_var, values=list(COMMON_PATTERNS.keys()), width=10, state='readonly', bootstyle='info')
        self.style_menu.grid(row=0, column=3, padx=6, sticky='w')

        tb.Label(control, text='Bars:', font=('Segoe UI', 11)).grid(row=0, column=4, sticky='w', padx=4)
        self.bars_var = tk.IntVar(value=4)
        self.bars_spin = tb.Spinbox(control, from_=1, to=16, textvariable=self.bars_var, width=5)
        self.bars_spin.grid(row=0, column=5, padx=6)

        tb.Label(control, text='Tempo (BPM):', font=('Segoe UI', 11)).grid(row=1, column=0, sticky='w', padx=4, pady=6)
        self.tempo_var = tk.IntVar(value=90)
        self.tempo_slider = tb.Scale(control, from_=40, to=200, orient='horizontal', variable=self.tempo_var, length=260, bootstyle='info')
        self.tempo_slider.grid(row=1, column=1, columnspan=3, sticky='w', padx=6)

        tb.Label(control, text='MIDI Device:', font=('Segoe UI', 11)).grid(row=1, column=4, sticky='w', padx=4)
        self.midi_var = tk.StringVar(value='(Auto)')
        self.midi_menu = tb.Combobox(control, textvariable=self.midi_var, values=[], width=28, state='readonly', bootstyle='info')
        self.midi_menu.grid(row=1, column=5, padx=6)

        # options
        options = tb.Frame(root)
        options.pack(fill='x', padx=12, pady=4)

        tb.Radiobutton(options, text='Block (ストローク)', variable=tk.StringVar(value='Block'), value='Block', bootstyle='outline-info').pack(side='left', padx=6)

        self.play_style_var = tk.StringVar(value='Block')
        tb.Radiobutton(options, text='Block (ストローク)', variable=self.play_style_var, value='Block', bootstyle='info').pack(side='left', padx=4)
        tb.Radiobutton(options, text='Arpeggio (アルペジオ)', variable=self.play_style_var, value='Arp', bootstyle='info').pack(side='left', padx=4)

        tb.Checkbutton(options, text='Loop', variable=tk.BooleanVar(value=False), bootstyle='success').pack_forget()  # placeholder
        self.loop_var = tk.BooleanVar(value=False)
        tb.Checkbutton(options, text='Loop', variable=self.loop_var, bootstyle='success').pack(side='left', padx=8)

        tb.Label(options, text='Inversion:', font=('Segoe UI', 10)).pack(side='left', padx=6)
        self.inversion_var = tk.IntVar(value=0)
        tb.Spinbox(options, from_=0, to=3, width=3, textvariable=self.inversion_var).pack(side='left')

        tb.Label(options, text='Octave shift:', font=('Segoe UI', 10)).pack(side='left', padx=6)
        self.octave_var = tk.IntVar(value=0)
        tb.Spinbox(options, from_=-2, to=2, width=3, textvariable=self.octave_var).pack(side='left')

        tb.Label(options, text='Velocity:', font=('Segoe UI', 10)).pack(side='left', padx=6)
        self.velocity_var = tk.IntVar(value=100)
        tb.Scale(options, from_=30, to=127, orient='horizontal', variable=self.velocity_var, length=120, bootstyle='info').pack(side='left', padx=6)

        tb.Label(options, text='Humanize (ms):', font=('Segoe UI', 10)).pack(side='left', padx=6)
        self.humanize_var = tk.IntVar(value=30)
        tb.Scale(options, from_=0, to=200, orient='horizontal', variable=self.humanize_var, length=120, bootstyle='primary').pack(side='left', padx=6)

        # output
        out_frame = tb.Labelframe(root, text='Generated Progression', bootstyle='secondary')
        out_frame.pack(fill='both', padx=12, pady=8, expand=True)

        self.output_text = tk.Text(out_frame, width=90, height=10, wrap='word', font=('Consolas', 11), bg='#0f1720', fg='#e6eef8')
        self.output_text.pack(padx=8, pady=8, fill='both', expand=True)

        # quick-buttons
        quick_frame = tb.Frame(root)
        quick_frame.pack(fill='x', padx=12, pady=6)

        self.generate_btn = tb.Button(quick_frame, text='Generate', bootstyle='success', command=self.on_generate)
        self.generate_btn.pack(side='left', padx=6)

        self.save_btn = tb.Button(quick_frame, text='Save', bootstyle='secondary', command=self.on_save)
        self.save_btn.pack(side='left', padx=6)

        self.play_btn = tb.Button(quick_frame, text='Play', bootstyle='info', command=self.on_play)
        self.play_btn.pack(side='left', padx=6)

        self.stop_btn = tb.Button(quick_frame, text='Stop', bootstyle='danger', command=self.on_stop)
        self.stop_btn.pack(side='left', padx=6)

        tb.Button(quick_frame, text='Export TXT', bootstyle='outline-secondary', command=self.export_txt).pack(side='left', padx=6)

        # chord quick play
        self.chord_buttons_frame = tb.Frame(root)
        self.chord_buttons_frame.pack(fill='x', padx=12, pady=6)

        # status
        self.status_var = tk.StringVar(value='Ready')
        status = tb.Label(root, textvariable=self.status_var, bootstyle='inverse-secondary')
        status.pack(fill='x', padx=12, pady=(0,8))

        root.protocol('WM_DELETE_WINDOW', self.on_close)

    def set_status(self, txt, timeout=None):
        self.status_var.set(txt)
        if timeout:
            self.root.after(timeout, lambda: self.status_var.set('Ready'))

    def populate_midi_devices(self):
        devs = MIDI.list_devices()
        out_devs = [f"{i}: {name}" for (i, name, is_out) in devs if is_out]
        if not out_devs:
            out_devs = ['(No MIDI output detected)']
        self.midi_menu.configure(values=['(Auto)'] + out_devs)
        self.midi_menu.set(self.settings.get('last_midi', '(Auto)'))

    def restore_settings(self):
        # restore UI states from settings
        s = self.settings
        if not s:
            return
        try:
            if 'key' in s: self.key_var.set(s['key'])
            if 'style' in s: self.style_var.set(s['style'])
            if 'bars' in s: self.bars_var.set(s['bars'])
            if 'tempo' in s: self.tempo_var.set(s['tempo'])
            if 'inversion' in s: self.inversion_var.set(s['inversion'])
            if 'octave' in s: self.octave_var.set(s['octave'])
            if 'velocity' in s: self.velocity_var.set(s['velocity'])
            if 'humanize' in s: self.humanize_var.set(s['humanize'])
        except Exception:
            pass

    def on_generate(self):
        for w in self.chord_buttons_frame.winfo_children():
            w.destroy()
        key = self.key_var.get()
        style = self.style_var.get()
        bars = int(self.bars_var.get())
        progression = generate_progression(key, style, bars)
        self.current_progression = progression
        result = f'Key: {key}    Style: {style}    Bars: {bars}\n\nProgression: | ' + ' | '.join(progression) + ' |\n\n'
        for chord in progression:
            result += f"{chord:6s} → {CHORD_SHAPES.get(chord,'-'):6s}\n"
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, result)
        # quick play buttons
        for chord in progression:
            btn = tb.Button(self.chord_buttons_frame, text=chord, width=8, bootstyle='outline-success', command=lambda c=chord: threading.Thread(target=self.safe_play_chord, args=(c,), daemon=True).start())
            btn.pack(side='left', padx=6, pady=4)
        self.set_status('Progression generated', 3000)

        # persist
        self.settings.update({'key': key, 'style': style, 'bars': bars, 'tempo': self.tempo_var.get()})
        save_settings(self.settings)

    def safe_play_chord(self, chord):
        try:
            self.ensure_midi_open()
            notes = chord_to_midi_notes(chord, octave=self.octave_var.get()*12, inversion=self.inversion_var.get())
            vel = self.velocity_var.get()
            for n in notes:
                MIDI.note_on(n, vel)
            time.sleep(0.9)
            for n in notes:
                MIDI.note_off(n)
        except Exception as e:
            print('play error:', e)
            self.set_status('Play error', 3000)

    def ensure_midi_open(self):
        choice = self.midi_var.get()
        if choice == '(Auto)':
            devs = MIDI.list_devices()
            outputs = [i for (i, name, is_out) in devs if is_out]
            if outputs:
                MIDI.open_output(outputs[0])
        else:
            try:
                dev_id = int(choice.split(':')[0])
                MIDI.open_output(dev_id)
                self.settings['last_midi'] = choice
                save_settings(self.settings)
            except Exception as e:
                print('cannot open selected device:', e)
                devs = MIDI.list_devices()
                outputs = [i for (i, name, is_out) in devs if is_out]
                if outputs:
                    MIDI.open_output(outputs[0])

    def on_play(self):
        if not self.current_progression:
            messagebox.showinfo('Info', 'まずGenerateで進行を生成してください。')
            return
        if self.play_thread and self.play_thread.is_alive():
            messagebox.showinfo('Info', '既に再生中です。')
            return
        self.play_flag.set()
        self.play_thread = threading.Thread(target=self.play_progression_loop, daemon=True)
        self.play_thread.start()
        self.set_status('Playing')

    def on_stop(self):
        self.play_flag.clear()
        self.set_status('Stopping', 800)
        # ensure notes off
        MIDI.all_notes_off()

    def play_progression_loop(self):
        try:
            self.ensure_midi_open()
        except:
            pass
        tempo = self.tempo_var.get()
        beat = 60.0 / tempo
        progression = self.current_progression[:]
        play_style = self.play_style_var.get()
        loop = self.loop_var.get()
        vel = self.velocity_var.get()
        humanize = self.humanize_var.get() / 1000.0

        try:
            while self.play_flag.is_set():
                for i, chord in enumerate(progression):
                    if not self.play_flag.is_set():
                        break
                    # highlight current chord in UI
                    self.highlight_chord_button(i)
                    notes = chord_to_midi_notes(chord, octave=self.octave_var.get()*12, inversion=self.inversion_var.get())
                    if play_style == 'Block':
                        # play together for 2 beats
                        jitter = random.uniform(-humanize, humanize)
                        for n in notes:
                            MIDI.note_on(n, vel)
                        time.sleep(max(0, beat*2 + jitter))
                        for n in notes:
                            MIDI.note_off(n)
                    else:
                        # arpeggio across 4 beats
                        total = beat * 4
                        step = total / max(1, len(notes))
                        for n in notes:
                            if not self.play_flag.is_set():
                                break
                            jitter = random.uniform(-humanize, humanize)
                            MIDI.note_on(n, vel)
                            time.sleep(max(0, step*0.9 + jitter))
                            MIDI.note_off(n)
                        time.sleep(0.05)
                if not loop:
                    break
        finally:
            self.clear_highlight()
            MIDI.all_notes_off()
            self.set_status('Ready')

    def highlight_chord_button(self, idx):
        # UI update must happen on main thread
        def _do():
            for i, w in enumerate(self.chord_buttons_frame.winfo_children()):
                try:
                    if i == idx:
                        w.configure(bootstyle='primary')
                    else:
                        w.configure(bootstyle='outline-success')
                except Exception:
                    pass
        self.root.after(1, _do)

    def clear_highlight(self):
        def _do():
            for w in self.chord_buttons_frame.winfo_children():
                try:
                    w.configure(bootstyle='outline-success')
                except Exception:
                    pass
        self.root.after(1, _do)

    def export_txt(self):
        if not self.current_progression:
            messagebox.showinfo('Info','保存する進行がありません。')
            return
        p = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text file','*.txt')])
        if not p:
            return
        with open(p,'w',encoding='utf-8') as f:
            f.write(self.output_text.get('1.0', tk.END))
        messagebox.showinfo('Saved', f'Saved to {p}')

    def on_save(self):
        # save current progression and settings
        if not self.current_progression:
            messagebox.showinfo('Info','保存する進行がありません。')
            return
        fpath = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')])
        if not fpath:
            return
        payload = {
            'progression': self.current_progression,
            'key': self.key_var.get(),
            'style': self.style_var.get(),
            'bars': self.bars_var.get(),
            'tempo': self.tempo_var.get()
        }
        with open(fpath,'w',encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        messagebox.showinfo('Saved', f'Saved to {fpath}')

    def on_close(self):
        self.play_flag.clear()
        try:
            if self.play_thread and self.play_thread.is_alive():
                self.play_thread.join(timeout=1.0)
        except Exception:
            pass
        MIDI.close()
        # save some settings
        self.settings.update({
            'key': self.key_var.get(), 'style': self.style_var.get(), 'bars': int(self.bars_var.get()),
            'tempo': int(self.tempo_var.get()), 'inversion': int(self.inversion_var.get()), 'octave': int(self.octave_var.get()),
            'velocity': int(self.velocity_var.get()), 'humanize': int(self.humanize_var.get())
        })
        save_settings(self.settings)
        self.root.destroy()


def main():
    root = tb.Window(themename='vapor')
    app = ChordApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
