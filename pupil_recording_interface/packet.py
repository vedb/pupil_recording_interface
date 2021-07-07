""""""


class Packet:
    """ A data packet with a timestamp and content. """

    def __init__(
        self,
        stream_name,
        device_uid,
        timestamp,
        source_timestamp=None,
        source_timebase="monotonic",
        broadcasts=None,
        display_hooks=None,
        **kwargs,
    ):
        """ Constructor. """
        self.stream_name = stream_name
        self.device_uid = device_uid
        self.timestamp = timestamp
        self.source_timestamp = source_timestamp or timestamp
        if source_timebase not in ("monotonic", "epoch"):
            raise ValueError(f"Unknown timebase: {source_timebase}")
        else:
            self.source_timebase = source_timebase
        self.broadcasts = broadcasts or []
        self.display_hooks = display_hooks or []

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __contains__(self, item):
        return hasattr(self, item)

    def __getitem__(self, item):
        return getattr(self, item)

    def __str__(self):
        return (
            f"pupil_recording_interface.Packet with data:\n"
            f"* stream_name: {self.stream_name}\n"
            f"* device_uid: {self.device_uid}\n"
            f"* timestamp: {self.timestamp}"
        )

    def __repr__(self):
        return self.__str__()

    def get_broadcasts(self):
        """"""
        return {broadcast: self[broadcast] for broadcast in self.broadcasts}
