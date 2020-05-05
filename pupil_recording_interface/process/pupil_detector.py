""""""
import os
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
        **kwargs,
    ):
        """ Constructor. """
        self.method = method
        self.camera_id = camera_id
        self.folder = folder
        self.record = record

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

            os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
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

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.pupil = self.call(self.detect_pupil, packet, block=block)

        if self.record:
            self.call(self.record_data, packet, block=block)

        packet.broadcasts.append("pupil")

        return packet

    def stop(self):
        """ Stop the process. """
        if self.writer is not None:
            self.writer.close()
