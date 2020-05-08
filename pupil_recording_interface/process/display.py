""""""
import warnings
import logging
from collections import deque

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

        # gaze overlay
        _queue_len = 5  # TODO constructor argument?
        self._eye0_gaze_deque = deque(maxlen=_queue_len)
        self._eye1_gaze_deque = deque(maxlen=_queue_len)
        self._binocular_gaze_deque = deque(maxlen=_queue_len)

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config,
            name=stream_config.name or device.device_uid,
            resolution=getattr(stream_config, "resolution", None),
        )
        if stream_config.name is not None:
            cls_kwargs["process_name"] = ".".join(
                (
                    stream_config.name,
                    cls_kwargs["process_name"] or cls.__name__,
                )
            )

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process. """
        try:
            cv2.namedWindow(
                self.name,
                cv2.WINDOW_NORMAL
                + cv2.WINDOW_KEEPRATIO
                + cv2.WINDOW_GUI_NORMAL,
            )
            if self.resolution is not None:
                cv2.resizeWindow(
                    self.name, self.resolution[0], self.resolution[1]
                )
        except cv2.error:
            pass

    def stop(self):
        """ Stop the process. """
        try:
            cv2.destroyWindow(self.name)
        except cv2.error:
            pass

    def process_notifications(self, notifications):
        """ Process new notifications. """
        # TODO avoid this duplication
        for notification in notifications:
            if (
                "pause_process" in notification
                and notification["pause_process"] == self.process_name
            ):
                self.stop()
            if (
                "resume_process" in notification
                and notification["resume_process"] == self.process_name
            ):
                self.start()

        super().process_notifications(notifications)

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

    def rggb_to_bgr(self, packet):
        """"""
        frame = packet["display_frame"]

        return cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2BGR)

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

        if packet.color_format == "bayer_rggb8":
            packet.display_frame = self.call(
                self.rggb_to_bgr,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

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
