""""""
import logging

import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.methods import normalize
from pupil_recording_interface.externals.file_methods import PLData_Writer

logger = logging.getLogger(__name__)


@process("pupil_detector")
class PupilDetector(BaseProcess):
    """ Pupil detector for eye video streams. """

    def __init__(
        self,
        method="2d c++",
        camera_id=None,
        folder=None,
        record=False,
        display=True,
        **kwargs,
    ):
        """ Constructor. """
        self.method = method
        self.camera_id = camera_id
        self.folder = folder
        self.record = record
        self.display = display

        super().__init__(**kwargs)

        if self.method not in ("2d c++",):
            raise ValueError(f"Unsupported detection method: {self.method}")

        self.detector = None

        if self.record:
            if self.folder is None:
                raise ValueError("folder cannot be None")
            self.writer = PLData_Writer(self.folder, "pupil")
        else:
            self.writer = None

    def start(self):
        """ Start the process. """
        if self.method == "2d c++":
            from pupil_detectors import Detector2D

            self.detector = Detector2D()
        else:
            raise ValueError(f"Unsupported detection method: {self.method}")

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config, folder=config.folder or kwargs.get("folder", None),
        )

        if cls_kwargs["camera_id"] is None:
            try:
                cls_kwargs["camera_id"] = int(stream_config.name[-1])
            except (ValueError, TypeError):
                try:
                    cls_kwargs["camera_id"] = int(stream_config.device_uid[-1])
                except (ValueError, TypeError):
                    logger.debug("Could not auto-determine eye camera ID")

        return cls(**cls_kwargs)

    def detect_pupil(self, packet):
        """ Detect pupil in frame. """
        frame = packet["frame"]

        if frame.ndim == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        pupil = self.detector.detect(frame)

        pupil["norm_pos"] = normalize(pupil["location"], frame.shape[1::-1])
        pupil["timestamp"] = packet["timestamp"]
        pupil["method"] = self.method
        pupil["id"] = self.camera_id
        pupil["topic"] = (
            f"pupil.{self.camera_id}" if self.camera_id else "pupil"
        )

        return pupil

    def record_data(self, packet):
        """ Write pupil datum to disk. """
        self.writer.append(packet["pupil"])

    def display_hook(self, packet):
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

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.pupil = self.call(self.detect_pupil, packet, block=block)

        if self.record:
            self.call(self.record_data, packet, block=block)

        packet.broadcasts.append("pupil")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet

    def stop(self):
        """ Stop the process. """
        if self.writer is not None:
            self.writer.close()
