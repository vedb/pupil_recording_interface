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
        pupil = packet["pupil"]
        if pupil is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR)

        ellipse = pupil["ellipse"]
        cv2.ellipse(
            frame,
            tuple(int(v) for v in ellipse["center"]),
            tuple(int(v / 2) for v in ellipse["axes"]),
            ellipse["angle"],
            0,
            360,  # start/end angle for drawing
            (0, 0, 255),  # color (BGR): red
        )

        return frame

    def _add_gaze_overlay(self, packet):
        """ Add gaze overlay onto frame. """
        gaze_points = packet["gaze_points"]
        if gaze_points is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        # TODO denormalize gaze point
        if len(gaze_points) == 0:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame
        elif len(gaze_points) == 1:
            gaze_point = int(gaze_points[0][0]), int(gaze_points[0][1])
        else:
            gaze_point = np.mean(gaze_points, axis=0)
            gaze_point = tuple(gaze_point.astype(int))

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR)

        # TODO make constructor arguments
        color = (0, 0, 255)
        radius = 10

        cv2.circle(frame, gaze_point, radius, color)

        return frame

    def _add_circle_grid_overlay(self, packet):
        """ Add circle grid overlay onto frame. """
        grid_points = packet["grid_points"]
        if grid_points is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR)

        calib_bounds = cv2.convexHull(grid_points).astype(np.int32)

        # TODO make constructor arguments
        color = (0, 0, 255)

        cv2.polylines(frame, [calib_bounds], True, color)

        return frame

    def show_frame(self, packet):
        """"""
        frame = packet["display_frame"]

        if frame is not None:
            cv2.imshow(self.name, frame)
            cv2.waitKey(1)

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.display_frame = packet.frame

        if self.overlay_pupil and "pupil" in packet:
            packet.display_frame = self.call(
                self._add_pupil_overlay,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        if self.overlay_gaze and "gaze_points" in packet:
            packet.display_frame = self.call(
                self._add_gaze_overlay,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        if self.overlay_circle_grid and "grid_points" in packet:
            packet.display_frame = self.call(
                self._add_circle_grid_overlay,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        # TODO make this non-blocking
        self.call(self.show_frame, packet, block=True)

        return packet
