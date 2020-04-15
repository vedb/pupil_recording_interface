""""""
import inspect
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


def get_params(cls):
    """ Get constructor parameters for a class. """
    signature = inspect.signature(cls.__init__)

    args = [
        name
        for name, param in signature.parameters.items()
        if param.kind is param.POSITIONAL_OR_KEYWORD
        and param.default is inspect._empty
    ]

    # remove instance parameter
    args = args[1:]

    kwargs = {
        name: param.default
        for name, param in signature.parameters.items()
        if param.kind is param.POSITIONAL_OR_KEYWORD
        and param.default is not inspect._empty
    }

    return args, kwargs


# TODO make BaseConfigurable method
def get_constructor_args(cls, config, **kwargs):
    """ Construct and instance of a class from a Config. """
    # get constructor signature
    cls_args, cls_kwargs = get_params(cls)

    # update matching keyword arguments
    for name, param in cls_kwargs.items():
        try:
            cls_kwargs[name] = getattr(config, name)
        except AttributeError:
            cls_kwargs[name] = param

    # update matching positional arguments
    for name in cls_args:
        if name not in cls_kwargs:
            try:
                cls_kwargs[name] = getattr(config, name)
            except AttributeError:
                # TODO the missing arguments can be supplied by
                #  kwargs. We should still check if all positional arguments
                #  are set at the end.
                pass

    cls_kwargs.update(kwargs)

    return cls_kwargs


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
