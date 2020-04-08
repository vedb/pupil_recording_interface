""""""
import logging
from concurrent.futures import Future, TimeoutError

logger = logging.getLogger(__name__)


class Packet:
    """ A data packet with a timestamp and content. """

    def __init__(
        self,
        timestamp,
        source_timestamp=None,
        source_timebase="monotonic",
        broadcasts=None,
        timeout=None,
        **kwargs,
    ):
        """ Constructor. """
        if source_timebase not in ("monotonic", "epoch"):
            raise ValueError(f"Unknown timebase: {source_timebase}")

        self.timestamp = timestamp
        self.source_timestamp = source_timestamp or timestamp
        self.source_timebase = source_timebase
        self.broadcasts = broadcasts or []
        self.timeout = timeout

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __contains__(self, item):
        return hasattr(self, item)

    def __getitem__(self, item):
        return getattr(self, item)

    def submit(self, executor, attr, func, *args, **kwargs):
        """"""
        setattr(self, attr, executor.submit(func, self, *args, **kwargs))

    def get(self, attr, timeout=None):
        """"""
        value = getattr(self, attr)
        if isinstance(value, Future):
            try:
                return value.result(timeout=timeout or self.timeout)
            except TimeoutError:
                return None
        else:
            return value

    def get_broadcasts(self):
        """"""
        return {
            broadcast: getattr(self, broadcast)
            for broadcast in self.broadcasts
        }
