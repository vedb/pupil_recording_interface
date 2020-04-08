""""""
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.utils import get_constructor_args

logger = logging.getLogger(__name__)


@process("video_display", optional=("name",))
class VideoDisplay(BaseProcess):
    """ Display for video stream. """

    def __init__(
        self,
        name,
        block=True,
        overlay_pupil=False,
        overlay_gaze=False,
        overlay_circle_grid=False,
        **kwargs,
    ):
        """ Constructor. """
        self.name = name
        self.overlay_pupil = overlay_pupil
        self.overlay_gaze = overlay_gaze
        self.overlay_circle_grid = overlay_circle_grid

        super().__init__(block=block, **kwargs)

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(
            cls, config, name=stream_config.name or device.device_uid
        )

        return cls(**cls_kwargs)

    def _add_pupil_overlay(self, packet):
        """ Add pupil overlay onto frame. """
        if packet.frame.ndim == 2:
            packet.frame = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR)

        ellipse = packet.pupil["ellipse"]
        cv2.ellipse(
            packet.frame,
            tuple(int(v) for v in ellipse["center"]),
            tuple(int(v / 2) for v in ellipse["axes"]),
            ellipse["angle"],
            0,
            360,  # start/end angle for drawing
            (0, 0, 255),  # color (BGR): red
        )

        return packet

    def _add_gaze_overlay(self, packet):
        """ Add gaze overlay onto frame. """
        if packet.frame.ndim == 2:
            packet.frame = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR)

        # TODO denormalize gaze point
        gaze_point = np.mean(packet.gaze_points, axis=0)
        gaze_point = tuple(gaze_point.astype(int))

        # TODO make constructor arguments
        color = (0, 0, 255)
        radius = 10

        cv2.circle(packet.frame, gaze_point, radius, color)

        return packet

    def _add_circle_grid_overlay(self, packet):
        """ Add circle grid overlay onto frame. """
        if packet.frame.ndim == 2:
            packet.frame = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR)

        calib_bounds = cv2.convexHull(packet.grid_points).astype(np.int32)

        # TODO make constructor arguments
        color = (0, 0, 255)

        cv2.polylines(packet.frame, [calib_bounds], True, color)

        return packet

    def show_frame(self, packet):
        """"""
        frame = packet.frame

        if frame is not None:
            cv2.imshow(self.name, frame)
            cv2.waitKey(1)

    def _process_packet(self, packet):
        """ Process a new packet. """
        if self.overlay_pupil and "pupil" in packet:
            packet = self._add_pupil_overlay(packet)

        if self.overlay_gaze and "gaze_points" in packet:
            packet = self._add_gaze_overlay(packet)

        if self.overlay_circle_grid and "grid_points" in packet:
            packet = self._add_circle_grid_overlay(packet)

        self.show_frame(packet)

        return packet
