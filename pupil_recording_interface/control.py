"""Functions to use to control recording devices"""
import simpleaudio
from pynput.keyboard import Key, Listener
import numpy as np

# Make ascending beep (WIP)

def make_beep():
    freq = 440
    fs = 44100
    seconds = .2
    t = np.linspace(0, seconds, fs * seconds)
    freqs = [440, 550, 660];
    note = np.hstack([np.sin(freq * t * 2 * np.pi) for freq in freqs])
    audio = (note * (2**15 - 1) / np.max(np.abs(note))).astype(np.int16)
    play_obj = simpleaudio.play_buffer(audio, 1, 2, fs)

# Show keypress collection (WIP)
def on_press(key):
    print('{0} pressed'.format(
        key))

def on_release(key):
    print('{0} release'.format(
        key))
    if key == Key.esc:
        # Stop listener
        return False

# Collect events until released
def collect_keypresses():
    with Listener(
            on_press=on_press,
            on_release=on_release) as listener:
        listener.join()
    
def control_listen():


def listen_demo():
    