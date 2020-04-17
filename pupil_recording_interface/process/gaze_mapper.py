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
        left="eye1",
        right="eye0",
        params=None,
        folder=None,
        record=False,
        block=False,
        **kwargs,
    ):
        """ Constructor. """
        self.left = left
        self.right = right
        self.params = params or [
            [
                22.06279309095615,
                27.233805896338197,
                -4.968271559107238,
                -3.0065855962823704,
                -13.47774849297383,
                -21.039823201325518,
                -79.63250746458891,
                174.32881820383022,
                2.927348015233868,
                1.165874665331882,
                4.186160094797165,
                -3.060545021023703,
                -3.5697134072793375,
            ],
            [
                51.57494601395783,
                50.96653289212003,
                -12.911423077545884,
                -0.9033969413550649,
                -33.73793257878155,
                -34.04548721522045,
                -183.9156834459527,
                413.4205868732686,
                7.679344281249296,
                -1.6095141228808707,
                14.952456135552591,
                -9.037791215096188,
                -8.995370243320579,
            ],
            13,
        ]
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
                        notification[self.right]["pupil"],
                        notification[self.left]["pupil"],
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
