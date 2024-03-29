""""""
from collections import deque
from queue import Queue
import logging
import warnings

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.gaze_mappers import (
    Binocular_Gaze_Mapper,
)
from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.externals.methods import denormalize

logger = logging.getLogger(__name__)

default_calibration = {
    "params": (
        [
            7.04514827765022,
            -6.648217956955106,
            -1.6468525493903128,
            2.5298454454735335,
            -6.869262035310202,
            5.0856896256604305,
            -8.334074360256515,
            12.466025180767396,
            1.155031280654134,
            -5.97662894498159,
            0.20685399567984675,
            2.944331996801389,
            2.2049977524270132,
        ],
        [
            16.956553174737163,
            22.92420616919661,
            7.025988262403478,
            8.973479069802556,
            -9.738102787522692,
            -16.13027740670349,
            -28.42731579187059,
            28.990781853882513,
            -5.613494277112884,
            -8.679905758623136,
            -14.300998802442034,
            22.12972070853907,
            -9.580819454962466,
        ],
        13,
    ),
    "params_eye0": (
        [
            -28.46704984072961,
            -29.403764212325378,
            15.483460496618992,
            14.88825931580099,
            41.57677527403535,
            -29.390288813732724,
            13.06470131282001,
        ],
        [
            2.5953055990057257,
            14.084313149121783,
            -2.424964344806809,
            -13.339353070208327,
            0.29392056195885896,
            0.006531943387444894,
            -3.5330844403445623,
        ],
        7,
    ),
    "params_eye1": (
        [
            -15.522538316193494,
            -21.952721337937096,
            7.610758381653593,
            17.305776752439826,
            44.92097000715874,
            -70.9514200310459,
            5.852297181221245,
        ],
        [
            20.989796195435105,
            29.689515309730538,
            -13.565682230187708,
            -20.358604071226992,
            -64.9871645353986,
            122.07999451270013,
            -6.792731418990433,
        ],
        7,
    ),
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
        display=True,
        **kwargs,
    ):
        """ Constructor. """
        self.left = left
        self.right = right
        self.min_confidence = min_confidence
        self.calibration = calibration or default_calibration
        self.folder = folder
        self.record = record
        self.display = display

        super().__init__(listen_for=["pupil"], **kwargs)

        self._gaze_queue = Queue()
        self.mapper = None

        if self.record:
            if self.folder is None:
                raise ValueError("folder cannot be None")
            self.writer = PLData_Writer(self.folder, "gaze")
        else:
            self.writer = None

        # gaze overlay
        _queue_len = 5  # TODO constructor argument?
        self._eye0_gaze_deque = deque(maxlen=_queue_len)
        self._eye1_gaze_deque = deque(maxlen=_queue_len)
        self._binocular_gaze_deque = deque(maxlen=_queue_len)

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

    def display_hook(self, packet):
        """ Add gaze overlay onto frame. """
        gaze = packet["gaze"]
        if gaze is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        frame = packet["display_frame"]
        gaze_points = [
            denormalize(g["norm_pos"], frame.shape[1::-1]) for g in gaze
        ]

        for idx, gaze_point in enumerate(gaze_points):
            if len(gaze[idx]["base_data"]) == 2:
                self._binocular_gaze_deque.append(gaze_point)
                self._eye0_gaze_deque.append((np.nan, np.nan))
                self._eye1_gaze_deque.append((np.nan, np.nan))
            elif gaze[idx]["base_data"][0]["id"] == 0:
                self._binocular_gaze_deque.append((np.nan, np.nan))
                self._eye0_gaze_deque.append(gaze_point)
                self._eye1_gaze_deque.append((np.nan, np.nan))
            elif gaze[idx]["base_data"][0]["id"] == 1:
                self._binocular_gaze_deque.append((np.nan, np.nan))
                self._eye0_gaze_deque.append((np.nan, np.nan))
                self._eye1_gaze_deque.append(gaze_point)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            binocular_gaze_point = np.nanmean(
                self._binocular_gaze_deque, axis=0
            )
            eye0_gaze_point = np.nanmean(self._eye0_gaze_deque, axis=0)
            eye1_gaze_point = np.nanmean(self._eye1_gaze_deque, axis=0)

        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # TODO make constructor arguments
        color = (0, 255, 0)
        radius = 10

        try:
            if not np.isnan(binocular_gaze_point).any():
                cv2.circle(
                    frame,
                    tuple(binocular_gaze_point.astype(int)),
                    radius,
                    color,
                    thickness=-1,
                )
            if not np.isnan(eye0_gaze_point).any():
                cv2.circle(
                    frame, tuple(eye0_gaze_point.astype(int)), radius, color,
                )
            if not np.isnan(eye1_gaze_point).any():
                cv2.circle(
                    frame, tuple(eye1_gaze_point.astype(int)), radius, color,
                )
        except OverflowError as e:
            logger.debug(e)

        return frame

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
                self.mapper = Binocular_Gaze_Mapper(
                    self.calibration["params"],
                    self.calibration["params_eye0"],
                    self.calibration["params_eye1"],
                )
                logger.info(
                    "Updated gaze mapper params with calibration results"
                )
            except (KeyError, TypeError):
                pass

        packet.gaze = self.call(self.get_mapped_gaze, block=block)

        if self.record:
            self.call(self.record_data, packet, block=block)

        packet.broadcasts.append("gaze")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet

    def start(self):
        """ Start the process. """
        self.mapper = Binocular_Gaze_Mapper(
            self.calibration["params"],
            self.calibration["params_eye0"],
            self.calibration["params_eye1"],
        )

    def stop(self):
        """ Stop the process. """
        self.mapper = None
        if self.writer is not None:
            self.writer.close()
