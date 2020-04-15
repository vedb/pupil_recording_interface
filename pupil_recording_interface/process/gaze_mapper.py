""""""
from queue import Queue
import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.utils import get_constructor_args
from pupil_recording_interface.externals.calibrate_2d import make_map_function
from pupil_recording_interface.externals.file_methods import PLData_Writer

logger = logging.getLogger(__name__)


@process("gaze_mapper")
class GazeMapper(BaseProcess):
    """ Gaze mapper. """

    def __init__(
        self,
        left="eye0",
        right="eye1",
        params=None,
        folder=None,
        record=False,
        block=False,
        **kwargs,
    ):
        """ Constructor. """
        self.left = left
        self.right = right
        # TODO sensible default params
        self.params = params or (
            [0.5, 0.1, 0.1, 0.1, 0.1],
            [-0.5, 0.1, 0.1, 0.1, 0.1],
            5,
        )
        self.folder = folder
        self.record = record

        super().__init__(block=block, listen_for=["pupil"], **kwargs)

        self._gaze_queue = Queue()
        self._map_fn = make_map_function(*self.params)

        if self.record:
            if self.folder is None:
                raise ValueError("folder cannot be None")
            self.writer = PLData_Writer(self.folder, "gaze")
        else:
            self.writer = None

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(
            cls, config, folder=config.folder or kwargs.get("folder", None),
        )

        return cls(**cls_kwargs)

    def map_gaze(self, pupil_0, pupil_1):
        """ Map gaze. """
        gaze_point = self._map_fn(pupil_0["norm_pos"], pupil_1["norm_pos"])
        confidence = (pupil_0["confidence"] + pupil_1["confidence"]) / 2.0
        ts = (pupil_0["timestamp"] + pupil_1["timestamp"]) / 2.0

        return {
            "topic": "gaze.2d.01.",
            "norm_pos": gaze_point,
            "confidence": confidence,
            "timestamp": ts,
            "base_data": [pupil_0, pupil_1],
        }

    def record_data(self, packet):
        """"""
        # TODO file size seems way too big
        for gaze in packet["gaze"]:
            self.writer.append(gaze)

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            try:
                self._gaze_queue.put(
                    self.map_gaze(
                        notification[self.left]["pupil"],
                        notification[self.right]["pupil"],
                    )
                )
            except KeyError:
                pass

    def _process_packet(self, packet, block=None):
        """ Process new data. """
        if "calibration_result" in packet:
            try:
                self.params = packet["calibration_result"]["args"]["params"]
                logger.info(
                    "Updated gaze mapper params with calibration results"
                )
            except KeyError:
                pass

        packet.gaze = []

        while not self._gaze_queue.empty():
            packet.gaze.append(self._gaze_queue.get())

        if self.record:
            self.call(self.record_data, packet, block=block)

        packet.broadcasts.append("gaze")

        return packet

    def stop(self):
        """"""
        if self.writer is not None:
            self.writer.close()
