""""""
import os
from queue import Queue
from uuid import uuid4
import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.utils import monotonic
from pupil_recording_interface.externals import GPoolDummy
from pupil_recording_interface.externals.finish_calibration import (
    select_method_and_perform_calibration,
)
from pupil_recording_interface.externals.file_methods import save_object

logger = logging.getLogger(__name__)


@process("validation", optional=("resolution",))
class Validation(BaseProcess):
    """ Validation during runtime class. """

    def __init__(
        self,
        resolution,
        mode="2d",
        min_confidence=0.8,
        left="eye1",
        right="eye0",
        world="world",
        name=None,
        folder=None,
        save=False,
        **kwargs,
    ):
        """ Constructor. """
        self.resolution = resolution
        self.mode = mode
        self.min_confidence = min_confidence
        self.left = left
        self.right = right
        self.world = world
        self.name = name or f"{self.mode} Validation"
        self.folder = folder
        self.save = save

        super().__init__(listen_for=["pupil"], **kwargs)

        if self.save and self.folder is None:
            raise ValueError("folder cannot be None")

        self.result = None
        self.uuid = None
        self.version = 1

        # TODO these need to be set
        self.recording_uuid = None
        self.frame_index_range = None

        self._collect = False
        self._calculated = False
        self._pupil_queue = Queue()
        self._circle_marker_queue = Queue()

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        # TODO this breaks when resolution is changed on the fly
        cls_kwargs = cls.get_constructor_args(
            config,
            resolution=stream_config.resolution,
            folder=config.folder or kwargs.get("folder", None),
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

    def save_result(self):
        """ Save result of calibration. """
        folder = os.path.join(os.path.expanduser(self.folder), "calibrations")
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(
            folder, f"{self.name.replace(' ', '_')}-{self.uuid}.plcal",
        )

        data = {
            "version": self.version,
            "data": [
                self.uuid,
                self.name,
                self.recording_uuid,
                self.mode,
                self.frame_index_range,
                self.min_confidence,
                "Validation successful",
                True,
                [self.result["name"], self.result["args"]],
            ],
        }

        save_object(data, filename)

        logger.info(f"Saved validation to {filename}")

        return filename

    def plot_markers(self, circle_marker_list):
        import matplotlib.pyplot as plt

        x = [c["img_pos"][0] for c in circle_marker_list]
        y = [c["img_pos"][1] for c in circle_marker_list]
        plt.plot(x, y, "ob", markersize=4, alpha=0.4)
        plt.xlim(0, 1280)
        plt.ylim(0, 1024)
        plt.grid(True)
        plt.savefig("covered_marker.png", dpi=200)
        plt.show()

        return True

    # Todo: This is just for demo purposes
    def clear_flag_dummy(self, packet):
        packet.calibration_calculated = True
        packet.broadcasts.append("calibration_calculated")

    def calculate_calibration(self):
        """ Calculate calibration from collected data. """
        # gather pupils
        pupil_list = []

        while not self._pupil_queue.empty():
            pupil_list.append(self._pupil_queue.get())

        # gather reference markers
        circle_marker_list = []
        while not self._circle_marker_queue.empty():
            # TODO get biggest circle marker
            circle_markers = self._circle_marker_queue.get()
            if len(circle_markers) > 0:
                circle_marker_list.append(circle_markers[0])

        # call calibration function
        g_pool = GPoolDummy(
            capture=GPoolDummy(frame_size=self.resolution),
            detection_mapping_mode=self.mode,
            min_calibration_confidence=self.min_confidence,
            get_timestamp=monotonic,
        )
        method, result = select_method_and_perform_calibration(
            g_pool, pupil_list, circle_marker_list
        )

        self._calculated = True

        # process result
        if result["subject"] == "calibration.failed":
            self.result = None
            logger.error("Calibration failed")
        else:
            self.result = self._fix_result(method, result)
            logger.info("Calibration successful")
            logger.debug(result)

            self.uuid = str(uuid4())

            if self.save:
                self.save_result()

        self.plot_markers(circle_marker_list)
        print("number of markers: ", len(circle_marker_list))
        print(
            "\n\nCalibration Markers:\n",
            [c["img_pos"] for c in circle_marker_list],
        )

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
                # logger.debug("Collecting calibration data")

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
            packet.collected_markers = self._circle_marker_queue.qsize()
            packet.broadcasts.append("collected_markers")

        if self._calculated:
            self.clear_flag_dummy(packet)
            if self.resolution != packet["frame"].shape[1::-1]:
                logger.warning(
                    f"Frame has resolution {packet['frame'].shape[1::-1]} "
                    f"but calibration was calculated for {self.resolution}"
                )
            packet.calibration_calculated = True
            packet.calibration_result = self.result
            self._calculated = False
        else:
            packet.calibration_calculated = False

        packet.broadcasts.append("calibration_calculated")

        return packet
