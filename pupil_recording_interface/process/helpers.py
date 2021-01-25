import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.device.video import VideoFileDevice

logger = logging.getLogger(__name__)


@process("video_file_syncer")
class VideoFileSyncer(BaseProcess):
    """ Syncer for VideoFileDevices. """

    def __init__(self, master_stream, check_every=100, **kwargs):
        """ Constructor. """
        self.master_stream = master_stream
        self.check_every = check_every

        super().__init__(
            listen_for=["timestamp", "source_timestamp"], **kwargs
        )

        self._last_master_ts = float("-inf")

    def start(self):
        """ Start the process. """
        if self.context is None or not isinstance(
            self.context.device, VideoFileDevice
        ):
            raise ValueError(
                "The VideoFileSyncer must be attached to a stream context "
                "that wraps a VideoFileDevice"
            )

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        notifications = [
            n[self.master_stream]
            for n in notifications
            if self.master_stream in n
        ]

        # check all notifications for looping
        for notification in notifications:
            ts = notification["timestamp"]
            if ts < self._last_master_ts:
                logger.debug("Detected looping of master stream")
                self.context.device.reset()
            self._last_master_ts = ts
