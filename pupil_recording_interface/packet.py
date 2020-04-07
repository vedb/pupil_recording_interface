""""""
from copy import deepcopy


class Packet:
    """ A data packet with a timestamp and content. """

    # TODO add get() method for Future attributes

    def __init__(
        self,
        timestamp,
        source_timestamp=None,
        source_timebase="monotonic",
        broadcasts=None,
        **kwargs,
    ):
        """ Constructor. """
        if source_timebase not in ("monotonic", "epoch"):
            raise ValueError(f"Unknown timebase: {source_timebase}")

        # TODO revisit this
        self._data = {
            "timestamp": timestamp,
            "source_timestamp": source_timestamp or timestamp,
            "source_timebase": source_timebase,
            "broadcasts": broadcasts or [],
        }

        self._data.update(kwargs)

    def __getattr__(self, item):
        try:
            return self._data[item]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        if key == "_data":
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, item):
        return self._data[item]

    def __contains__(self, item):
        return item in self._data

    def to_dict(self, deep=True):
        """ Convert to dict. """
        if deep:
            return deepcopy(self._data)
        else:
            return self._data.copy()

    def copy(self, deep=True):
        """ Create a copy of this instance. """
        return type(self)(**self.to_dict(deep=deep))

    def get_broadcasts(self):
        """"""
        return {b: self[b] for b in self.broadcasts}
