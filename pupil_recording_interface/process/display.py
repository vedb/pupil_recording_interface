""""""
import logging
import warnings

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def deprecation_warning(argument_name, process_name):
    msg = (
        f"The '{argument_name}' argument is deprecated and has no effect. "
        f"It is replaced by the 'display' argument in {process_name}."
    )
    warnings.warn(DeprecationWarning(msg))


@process("video_display", optional=("name",))
class VideoDisplay(BaseProcess):
    """ Display for video stream. """

    def __init__(
        self,
        name,
        flip=False,
        resolution=None,
        max_width=None,
        overlay_pupil=None,
        overlay_gaze=None,
        overlay_circle_marker=None,
        overlay_circle_grid=None,
        block=True,
        **kwargs,
    ):
        """ Constructor. """
        self.name = name
        self.flip = flip
        self.resolution = resolution
        self.max_width = max_width

        # deprecated arguments
        if overlay_pupil is not None:
            deprecation_warning("overlay_pupil", "PupilDetector")
        if overlay_gaze is not None:
            deprecation_warning("overlay_gaze", "GazeMapper")
        if overlay_circle_marker is not None:
            deprecation_warning("overlay_circle_marker", "CircleDetector")
        if overlay_circle_grid is not None:
            deprecation_warning("overlay_circle_grid", "CircleGridDetector")

        super().__init__(block=block, **kwargs)

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

    def create_window(self):
        """ Create a cv2.namedWindow. """
        try:
            cv2.namedWindow(
                self.name,
                cv2.WINDOW_NORMAL
                + cv2.WINDOW_KEEPRATIO
                + cv2.WINDOW_GUI_NORMAL,
            )
            if self.resolution is not None:
                if (
                    self.max_width is not None
                    and self.resolution[0] > self.max_width
                ):
                    cv2.resizeWindow(
                        self.name,
                        self.max_width,
                        int(
                            self.resolution[1]
                            / self.resolution[0]
                            * self.max_width
                        ),
                    )
                else:
                    cv2.resizeWindow(
                        self.name, self.resolution[0], self.resolution[1]
                    )
        except cv2.error:
            pass

    def close_window(self):
        """ Close the window for this process. """
        try:
            cv2.destroyWindow(self.name)
        except cv2.error:
            pass

    def start(self):
        """ Start the process. """
        if not self.paused:
            self.create_window()

    def stop(self):
        """ Stop the process. """
        self.close_window()

    def process_notifications(self, notifications):
        """ Process new notifications. """
        # TODO avoid this duplication
        for notification in notifications:
            if (
                "pause_process" in notification
                and notification["pause_process"] == self.process_name
            ):
                self.close_window()
            if (
                "resume_process" in notification
                and notification["resume_process"] == self.process_name
            ):
                self.create_window()

        super().process_notifications(notifications)

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
        # check if window was closed and pause process
        try:
            if cv2.getWindowProperty(self.name, cv2.WND_PROP_VISIBLE) < 1:
                logger.debug(
                    f"Window '{self.name}' was closed, pausing process"
                )
                self.paused = True
                return packet
        except cv2.error:
            pass

        packet.display_frame = packet.frame

        if packet.color_format == "bayer_rggb8":
            packet.display_frame = self.call(
                self.rggb_to_bgr,
                packet,
                block=block,
                return_if_full=packet.display_frame,
            )

        for hook in packet.display_hooks:
            packet.display_frame = self.call(
                hook, packet, block=block, return_if_full=packet.display_frame,
            )

        # TODO make this non-blocking
        self.call(self.show_frame, packet, block=True)

        return packet
