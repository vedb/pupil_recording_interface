""""""
from queue import Queue
import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.utils import get_constructor_args
from pupil_recording_interface.externals import GPoolDummy
from pupil_recording_interface.externals.finish_calibration import (
    select_method_and_perform_calibration,
)

logger = logging.getLogger(__name__)


@process("calibration", optional=("resolution",))
class Calibration(BaseProcess):
    """ Calibration. """

    def __init__(
        self,
        resolution,
        mode="2d",
        min_confidence=0.8,
        left="eye1",
        right="eye0",
        world="world",
        block=False,
        **kwargs,
    ):
        """ Constructor. """
        self.resolution = resolution
        self.mode = mode
        self.min_confidence = min_confidence
        self.left = left
        self.right = right
        self.world = world

        super().__init__(block=block, listen_for=["pupil"], **kwargs)

        self.result = None
        self._collect = False
        self._calculated = False
        self._pupil_queue = Queue()
        self._circle_marker_queue = Queue()

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        # TODO this breaks when resolution is changed on the fly
        cls_kwargs = get_constructor_args(
            cls, config, resolution=stream_config.resolution,
        )

        return cls(**cls_kwargs)

    @classmethod
    def _fix_result(cls, method, result):
        """ Fix result to match calibration obtained by Pupil Software. """
        # TODO find out why and get rid of this method
        if method == "binocular polynomial regression":
            # y parameters are flipped
            result["args"]["params"] = (
                result["args"]["params"][0],
                [-p for p in result["args"]["params"][1]],
                result["args"]["params"][2],
            )
            result["args"]["params_eye0"] = (
                result["args"]["params_eye0"][0],
                [-p for p in result["args"]["params_eye0"][1]],
                result["args"]["params_eye0"][2],
            )
            result["args"]["params_eye1"] = (
                result["args"]["params_eye1"][0],
                [-p for p in result["args"]["params_eye1"][1]],
                result["args"]["params_eye1"][2],
            )
            # last coefficients are exactly one off
            result["args"]["params"][1][-1] += 1
            result["args"]["params_eye0"][1][-1] += 1
            result["args"]["params_eye1"][1][-1] += 1

        return result

    def calculate_calibration(self):
        """ Calculate calibration from collected data. """
        pupil_list = []
        while not self._pupil_queue.empty():
            pupil_list.append(self._pupil_queue.get())

        circle_marker_list = []
        while not self._circle_marker_queue.empty():
            # TODO get biggest circle marker
            circle_markers = self._circle_marker_queue.get()
            if len(circle_markers) > 0:
                circle_marker_list.append(circle_markers[0])

        g_pool = GPoolDummy(
            capture=GPoolDummy(frame_size=self.resolution),
            detection_mapping_mode=self.mode,
            min_calibration_confidence=self.min_confidence,
        )
        method, result = select_method_and_perform_calibration(
            g_pool, pupil_list, circle_marker_list
        )
        self.result = self._fix_result(method, result)

        logger.info("Calculated calibration")
        self._calculated = True

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            # check for triggers
            if (
                "calculate_calibration" in notification
                and notification["calculate_calibration"]
            ):
                self._collect = False
                self._calculated = False
                self.call(self.calculate_calibration, block=block)
            elif (
                "collect_calibration_data" in notification
                and notification["collect_calibration_data"]
            ):
                self._collect = True
                logger.debug("Collecting calibration data")

            # collect new data
            if self._collect:
                try:
                    self._pupil_queue.put(notification[self.left]["pupil"])
                except KeyError:
                    pass

                try:
                    self._pupil_queue.put(notification[self.right]["pupil"])
                except KeyError:
                    pass

    def _process_packet(self, packet, block=None):
        """ Process a packet. """
        if self._collect and "circle_markers" in packet:
            self._circle_marker_queue.put(packet["circle_markers"])

        if self._calculated:
            if self.resolution != packet["frame"].shape[1::-1]:
                logger.warning(
                    f"Frame has resolution {packet['frame'].shape[1::-1]} "
                    f"but calibration was calculated for {self.resolution}"
                )

            packet.calibration_calculated = True
            packet.calibration_result = self.result
            packet.broadcasts.append("calibration_calculated")

            self._calculated = False

        return packet
