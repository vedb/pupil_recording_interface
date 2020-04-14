""""""
import logging
from concurrent.futures import Future

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
        return self.get(item)

    def get(self, attr, timeout=None):
        """

        Parameters
        ----------
        attr
        timeout

        Returns
        -------

        Raises
        ------

        """
        value = getattr(self, attr)
        if isinstance(value, Future):
            if timeout is None:
                timeout = self.timeout
            return value.result(timeout=timeout)
        else:
            return value

    def get_broadcasts(self):
        """"""
        return {broadcast: self[broadcast] for broadcast in self.broadcasts}