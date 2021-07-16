""""""
import logging
from typing import Optional

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess

logger = logging.getLogger(__name__)


@process("video_display", optional=("name",))
class VideoDisplay(BaseProcess):
    """ Display for video stream.

    This process displays camera frames produced by video streams. Previous
    processes in the pipeline can add overlays onto the frame, e.g., detected
    pupils or calibration markers, if they are created with ``display=True``.
    This process should generally be the last in the pipeline.
    """

    def __init__(
        self,
        name: str,
        flip: bool = False,
        resolution: Optional[tuple] = None,
        max_width: Optional[int] = None,
        block=True,
        **kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        name:
            Name of the video display.

        flip:
            If True, flip the image in the vertical direction. May be necessary
            for one of the eye camera streams.

        resolution:
            If specified, scale the window to this resolution.

        max_width:
            If specified, scale the window to this width if it would be wider.
        """
        self.name = name
        self.flip = flip
        self.resolution = resolution
        self.max_width = max_width

        super().__init__(block=block, **kwargs)

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls._get_constructor_args(
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
        if not self.paused:
            self.create_window()

    def stop(self):
        """ Stop the process. """
        self.close_window()

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
        except cv2.error as e:
            logger.debug(f"Failed to open window {self.name}, reason: {e}")

    def close_window(self):
        """ Close the window for this process. """
        try:
            cv2.destroyWindow(self.name)
        except cv2.error as e:
            logger.debug(f"Failed to close window {self.name}, reason: {e}")

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

    def _process_packet(self, packet):
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

        # convert to BGR if necessary
        if packet.color_format == "bayer_rggb8":
            packet.display_frame = self._rggb_to_bgr(packet)

        for hook in packet.display_hooks:
            packet.display_frame = hook(packet)

        packet.keypress = self.show_frame(packet)

        if packet.keypress is not None:
            packet.broadcasts.append("keypress")

        return packet

    @staticmethod
    def _rggb_to_bgr(packet):
        """ Convert RGGB to BGR. """
        frame = packet["display_frame"]

        return cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2BGR)

    def show_frame(self, packet):
        """ Show video frame in window. """
        frame = packet["display_frame"]

        if self.flip:
            frame = np.rot90(frame, 2)

        if frame is not None:
            cv2.imshow(self.name, frame)
            key = cv2.waitKey(1)
            if key != -1:
                logger.debug(f"Captured keypress: {chr(key)}")
                return chr(key)
