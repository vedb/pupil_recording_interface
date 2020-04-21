""""""
import logging
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
