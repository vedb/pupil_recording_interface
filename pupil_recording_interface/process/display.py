""""""
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.methods import denormalize

logger = logging.getLogger(__name__)


@process("video_display", optional=("name",))
class VideoDisplay(BaseProcess):
    """ Display for video stream. """

    def __init__(
        self,
        name,
        flip=False,
        resolution=None,
        overlay_pupil=False,
        overlay_gaze=False,
        overlay_circle_marker=False,
        overlay_circle_grid=False,
        block=True,
        **kwargs,
    ):
        """ Constructor. """
        self.name = name
        self.flip = flip
        self.resolution = resolution
        self.overlay_pupil = overlay_pupil
        self.overlay_gaze = overlay_gaze
        self.overlay_circle_marker = overlay_circle_marker
        self.overlay_circle_grid = overlay_circle_grid

        super().__init__(block=block, **kwargs)

        self._last_gaze_point = None

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config,
            name=stream_config.name or device.device_uid,
            resolution=getattr(stream_config, "resolution", None),
        )

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process. """
        cv2.namedWindow(
            self.name,
            cv2.WINDOW_NORMAL + cv2.WINDOW_KEEPRATIO + cv2.WINDOW_GUI_NORMAL,
        )
        if self.resolution is not None:
            cv2.resizeWindow(self.name, self.resolution[0], self.resolution[1])

    def _add_pupil_overlay(self, packet):
        """ Add pupil overlay onto frame. """
        pupil = packet["pupil"]
        if pupil is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

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
        gaze = packet["gaze"]
        if gaze is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        frame = packet["display_frame"]
        gaze_points = [
            denormalize(g["norm_pos"], frame.shape[1::-1]) for g in gaze
        ]

        # TODO smoothed + timeout or similar
        if len(gaze_points) == 0:
            gaze_point = self._last_gaze_point
        elif len(gaze_points) == 1:
            gaze_point = int(gaze_points[0][0]), int(gaze_points[0][1])
        else:
            gaze_point = np.mean(gaze_points, axis=0)
            gaze_point = tuple(gaze_point.astype(int))
        self._last_gaze_point = gaze_point

        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # TODO make constructor arguments
        color = (0, 255, 0)
        radius = 10

        try:
            cv2.circle(frame, gaze_point, radius, color, thickness=-1)
        except OverflowError as e:
            logger.debug(e)

        return frame

    def _add_circle_marker_overlay(self, packet):
        """ Add gaze overlay onto frame. """
        circle_markers = packet["circle_markers"]
        if circle_markers is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        if len(circle_markers) == 0:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame
        else:
            # TODO get the largest marker
            marker_position = (
                int(circle_markers[0]["img_pos"][0]),
                int(circle_markers[0]["img_pos"][1]),
            )

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # TODO make constructor arguments
        color = (255, 0, 0)
        radius = 20

        cv2.circle(frame, marker_position, radius, color)

        return frame

    def _add_circle_grid_overlay(self, packet):
        """ Add circle grid overlay onto frame. """
        circle_grid = packet["circle_grid"]
        if circle_grid is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame
        else:
            grid_points = circle_grid["grid_points"]

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        if isinstance(grid_points, list):
            calib_bounds = [
                cv2.convexHull(gp).astype(np.int32) for gp in grid_points
            ]
        else:
            calib_bounds = [cv2.convexHull(grid_points).astype(np.int32)]

        # TODO make constructor arguments
        color = (0, 255, 0)

        cv2.polylines(frame, calib_bounds, True, color)

        return frame

    def show_frame(self, packet):
        """"""
        frame = packet["display_frame"]

        if self.flip:
            frame = np.rot90(frame, 2)

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

        if self.overlay_gaze and "gaze" in packet:
            packet.display_frame = self.call(
                self._add_gaze_overlay,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        if self.overlay_circle_marker and "circle_markers" in packet:
            packet.display_frame = self.call(
                self._add_circle_marker_overlay,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        if self.overlay_circle_grid and "circle_grid" in packet:
            packet.display_frame = self.call(
                self._add_circle_grid_overlay,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        # TODO make this non-blocking
        self.call(self.show_frame, packet, block=True)

        return packet
