""""""
import logging
import os
import sys
import io
from collections import deque
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing.managers import SyncManager
from queue import Queue
from pathlib import Path
import multiprocessing as mp

import numpy as np

logger = logging.getLogger(__name__)

SyncManager.register("deque", deque)

try:
    from uvc import get_time_monotonic as monotonic  # noqa
except ImportError:
    logger.debug("Could not import uvc, falling back to time.monotonic")
    from time import monotonic  # noqa

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = None


def identify_process(process_type, name=None):
    """"""
    name = name or mp.current_process().name
    logger.debug(f"Process ID for {process_type} {name}: {os.getpid()}")
    if setproctitle is not None:
        setproctitle(name)


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
        try:
            self.orig_stream_fileno = stream.fileno()
        except io.UnsupportedOperation:
            self.orig_stream_fileno = None

    def __enter__(self):
        if self.orig_stream_fileno is not None:
            self.orig_stream_dup = os.dup(self.orig_stream_fileno)
            self.devnull = open(os.devnull, "w")
            os.dup2(self.devnull.fileno(), self.orig_stream_fileno)

    def __exit__(self, type, value, traceback):
        if self.orig_stream_fileno is not None:
            os.close(self.orig_stream_fileno)
            os.dup2(self.orig_stream_dup, self.orig_stream_fileno)
            os.close(self.orig_stream_dup)
            self.devnull.close()


def get_test_recording(version="2.0"):
    """ Get a short test recording for demonstration.

    The recording will be automatically downloaded and cached. The method
    returns a path to the cache location that can be used in reader methods
    and classes.

    Parameters
    ----------
    version: str, default "2.0"
        Pupil Player version used for post-hoc gaze mapping. Can be
        "1.16" or "2.0".

    Returns
    -------
    recording: pathlib.Path
        Path to the test recording.
    """
    try:
        import pooch
        from pooch import Unzip
    except ImportError:
        raise ModuleNotFoundError(
            "pooch must be installed to load example data"
        )

    url = "https://github.com/vedb/pupil-example-data/archive/refs/heads/"

    goodboy = pooch.create(
        path=pooch.os_cache("pupil-example-data"),
        base_url=url,
        registry={"branch-v1.16.zip": None, "branch-v2.0.zip": None},
    )

    fnames = goodboy.fetch(f"branch-v{version}.zip", processor=Unzip())

    return Path(fnames[0]).parent


def merge_pupils(pupils_eye0, pupils_eye1):
    """ Merge detected pupils from both eyes, sorted by timestamp.

    Parameters
    ----------
    pupils_eye0 : list of dict
        Detected pupils from the first eye.

    pupils_eye1 : list of dict
        Detected pupils from the second eye.

    Returns
    -------
    pupils : list of dict
        Merged pupils.
    """
    pupils = sorted(pupils_eye0 + pupils_eye1, key=lambda p: p["timestamp"])

    return pupils
