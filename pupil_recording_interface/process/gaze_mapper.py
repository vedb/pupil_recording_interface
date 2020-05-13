""""""
from queue import Queue
import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.gaze_mappers import (
    Binocular_Gaze_Mapper,
)
from pupil_recording_interface.externals.file_methods import PLData_Writer

logger = logging.getLogger(__name__)

default_calibration = {
    "params": [
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
    ],
    "params_eye0": [
        [
            -5.573642210122941,
            -15.660366268881239,
            3.3892265084323627,
            15.491778221191906,
            24.61607970636751,
            -37.56048142264788,
            2.8102198453565217,
        ],
        [
            -4.449380270968307,
            -4.243154731676149,
            4.098351002412766,
            0.6817178913459605,
            0.7913556940415702,
            -3.397681472038215,
            2.8006933001301615,
        ],
        7,
    ],
    "params_eye1": [
        [
            -6.0625412029505625,
            -1.308220620996945,
            3.314804406714515,
            -0.1758573135817958,
            5.839207978162214,
            -3.9934924304376267,
            1.7932222025398197,
        ],
        [
            -59.64240627663011,
            -6.624310160582425,
            40.491922926613995,
            -4.079075716683576,
            84.13402791986088,
            -78.37694504349447,
            7.209455805477312,
        ],
        7,
    ],
}


@process("gaze_mapper")
class GazeMapper(BaseProcess):
    """ Gaze mapper. """

    def __init__(
        self,
        left="eye1",
        right="eye0",
        min_confidence=0.8,
        calibration=None,
        folder=None,
        record=False,
        block=False,
        **kwargs,
    ):
        """ Constructor. """
        self.left = left
        self.right = right
        self.min_confidence = min_confidence
        self.calibration = calibration or default_calibration
        self.folder = folder
        self.record = record

        super().__init__(block=block, listen_for=["pupil"], **kwargs)

        self._gaze_queue = Queue()
        self.mapper = Binocular_Gaze_Mapper(
            self.calibration["params"],
            self.calibration["params_eye0"],
            self.calibration["params_eye1"],
        )

        if self.record:
            if self.folder is None:
                raise ValueError("folder cannot be None")
            self.writer = PLData_Writer(self.folder, "gaze")
        else:
            self.writer = None

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config, folder=config.folder or kwargs.get("folder", None),
        )

        return cls(**cls_kwargs)

    def get_mapped_gaze(self):
        """ Call the pupil gaze mapper. """
        gaze = []
        while not self._gaze_queue.empty():
            gaze.append(self._gaze_queue.get())

        return gaze

    def record_data(self, packet):
        """ Record gaze to disk. """
        for gaze in packet["gaze"]:
            self.writer.append(gaze)

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            if (
                self.left in notification
                and "pupil" in notification[self.left]
            ):
                for gaze in self.mapper.on_pupil_datum(
                    notification[self.left]["pupil"]
                ):
                    self._gaze_queue.put(gaze)
            if (
                self.right in notification
                and "pupil" in notification[self.right]
            ):
                for gaze in self.mapper.on_pupil_datum(
                    notification[self.right]["pupil"]
                ):
                    self._gaze_queue.put(gaze)

    def _process_packet(self, packet, block=None):
        """ Process new data. """
        if "calibration_result" in packet:
            try:
                self.calibration = packet["calibration_result"]["args"][
                    "params"
                ]
                logger.info(
                    "Updated gaze mapper params with calibration results"
                )
            except (KeyError, TypeError):
                pass

        packet.gaze = self.call(self.get_mapped_gaze, block=block)

        if self.record:
            self.call(self.record_data, packet, block=block)

        packet.broadcasts.append("gaze")

        return packet

    def stop(self):
        """ Stop the process. """
        if self.writer is not None:
            self.writer.close()
