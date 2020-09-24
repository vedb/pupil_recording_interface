""""""
import logging
import os
import sys
from collections import deque
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing.managers import SyncManager
from queue import Queue

logger = logging.getLogger(__name__)

SyncManager.register("deque", deque)

try:
    from uvc import get_time_monotonic as monotonic  # noqa
except ImportError:
    logger.warning("Could not import uvc, falling back to time.monotonic")
    from time import monotonic  # noqa


def multiprocessing_deque(maxlen=None):
    """"""
    manager = SyncManager()
    manager.start()
    return manager.deque(maxlen=maxlen)


class DroppingThreadPoolExecutor(ThreadPoolExecutor):
    """"""

    def __init__(self, maxsize=None, *args, **kwargs):
        """"""
        super().__init__(*args, **kwargs)
        self._work_queue = Queue(maxsize=maxsize)

    def qsize(self):
        """"""
        return self._work_queue.qsize()

    def full(self):
        """"""
        return self._work_queue.full()

    def submit(self, fn, *args, return_if_full=None, **kwargs):
        """"""
        if self.full():
            return return_if_full
        else:
            return super().submit(fn, *args, **kwargs)


class SuppressStream:
    """ Context manager for suppressing low-level stdout/stderr writes.

    From https://stackoverflow.com/a/57677370/4532781
    """

    def __init__(self, stream=sys.stderr):
        self.orig_stream_fileno = stream.fileno()

    def __enter__(self):
        self.orig_stream_dup = os.dup(self.orig_stream_fileno)
        self.devnull = open(os.devnull, "w")
        os.dup2(self.devnull.fileno(), self.orig_stream_fileno)

    def __exit__(self, type, value, traceback):
        os.close(self.orig_stream_fileno)
        os.dup2(self.orig_stream_dup, self.orig_stream_fileno)
        os.close(self.orig_stream_dup)
        self.devnull.close()

def beep(freq=440, fs=44100, seconds=0.1):
    """ Make a beep noise to indicate recording state. """
    import numpy as np
    import simpleaudio
    t = np.linspace(0, seconds, int(fs * seconds))
    if not isinstance(freq, list):
        freq = [freq]
    notes = np.hstack([np.sin(f * t * 2 * np.pi) for f in freq])
    audio = (notes * (2 ** 15 - 1) / np.max(np.abs(notes))).astype(np.int16)
    simpleaudio.play_buffer(audio, 1, 2, fs)
