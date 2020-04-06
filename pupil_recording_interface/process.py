import abc
import os
import logging
from concurrent.futures import ThreadPoolExecutor, Future

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.encoder import VideoEncoderFFMPEG
from pupil_recording_interface.utils import get_constructor_args

logger = logging.getLogger(__name__)


class BaseProcess:
    """ Base class for all processes. """

    def __init__(self, block=True, **kwargs):
        """ Constructor. """
        self.block = block

        self._executor = ThreadPoolExecutor()

    @classmethod
    def from_config(cls, config, stream_config, device, **kwargs):
        """ Create a process from a StreamConfig. """
        try:
            return process.registry[config.process_type]._from_config(
                config, stream_config, device, **kwargs
            )
        except KeyError:
            raise ValueError(
                f"No such process type: {config.process_type}. "
                f"If you are implementing a custom process, remember to use "
                f"the @pupil_recording_interface.process class decorator."
            )

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(cls, config)

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process"""

    def process_packet(self, packet):
        """ Process a new packet. """
        if isinstance(packet, Future):
            # TODO timeout?
            packet = packet.result()

        if self.block:
            return self._process_packet(packet)
        else:
            # TODO this still doesn't help if the processing takes longer
            #  than the packet interval
            return self._executor.submit(self._process_packet, packet)

    @abc.abstractmethod
    def _process_packet(self, packet):
        """ Process a new packet. """

    def stop(self):
        """ Stop the process. """


@process("video_display")
class VideoDisplay(BaseProcess):
    """ Display for video stream. """

    def __init__(self, name, overlay_pupil=False, **kwargs):
        """ Constructor. """
        self.name = name
        self.overlay_pupil = overlay_pupil

        super().__init__(**kwargs)

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(
            cls, config, name=stream_config.name or device.device_uid
        )

        return cls(**cls_kwargs)

    def _process_packet(self, packet):
        """ Process a new packet. """
        if self.overlay_pupil and "pupil" in packet:
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

        cv2.imshow(self.name, packet.frame)
        cv2.waitKey(1)

        return packet


class BaseRecorder(BaseProcess):
    """ Recorder for stream. """

    def __init__(self, folder, name=None, **kwargs):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        name: str, optional
            The name of the recorder.
        """
        if folder is None:
            raise ValueError("Recording folder cannot be None")
        else:
            self.folder = folder

        self.name = name

        super().__init__(**kwargs)

    @abc.abstractmethod
    def write(self, data):
        """ Write data to disk. """


@process("video_recorder")
class VideoRecorder(BaseRecorder):
    """ Recorder for a video stream. """

    def __init__(
        self,
        folder,
        resolution,
        fps,
        name=None,
        color_format="bgr24",
        codec="libx264",
        **encoder_kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        device: BaseVideoDevice
            The device from which to record the video.

        name: str, optional
            The name of the recorder. If not specified, `device.device_uid`
            will be used.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        encoder_kwargs:
            Addtional keyword arguments passed to the encoder.
        """
        super(VideoRecorder, self).__init__(folder, name=name)

        self.encoder = VideoEncoderFFMPEG(
            self.folder,
            self.name,
            resolution,
            fps,
            color_format,
            codec,
            overwrite=False,
            **encoder_kwargs,
        )

        self.timestamp_file = os.path.join(
            self.folder, f"{self.name}_timestamps.npy"
        )
        if os.path.exists(self.timestamp_file):
            raise IOError(f"{self.timestamp_file} exists, will not overwrite")

        self._timestamps = []

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(
            cls,
            config,
            folder=config.folder or kwargs.get("folder", None),
            resolution=config.resolution or device.resolution,
            fps=config.fps or device.fps,
            name=stream_config.name or device.device_uid,
            color_format=config.color_format or stream_config.color_format,
        )

        return cls(**cls_kwargs)

    def write(self, frame):
        """ Write data to disk. """
        self.encoder.write(frame)

    def _process_packet(self, packet):
        """ Process a new packet. """
        self.write(packet.frame)
        self._timestamps.append(packet.timestamp)

        return packet

    def stop(self):
        """ Stop the recorder. """
        self.encoder.stop()
        # TODO additionally save timestamps continuously if paranoid=True
        np.save(self.timestamp_file, np.array(self._timestamps))


@process("odometry_recorder")
class OdometryRecorder(BaseRecorder):
    """ Recorder for an odometry stream. """

    def __init__(self, folder, name=None, topic="odometry"):
        """ Constructor. """
        super(OdometryRecorder, self).__init__(folder, name=name)

        self.filename = os.path.join(self.folder, topic + ".pldata")
        if os.path.exists(self.filename):
            raise IOError(f"{self.filename} exists, will not overwrite")
        self.writer = PLData_Writer(self.folder, topic)

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        return cls(config.folder or kwargs.get("folder", None))

    def start(self):
        """ Start the recorder. """
        logger.debug(
            f"Started odometry recorder, recording to {self.filename}"
        )

    def write(self, data):
        """ Write data to disk. """
        self.writer.append(data)

    def _process_packet(self, packet):
        """ Process a new packet. """
        self.write(packet.odometry)

        return packet

    def stop(self):
        """ Stop the recorder. """
        self.writer.close()


@process("pupil_detector")
class PupilDetector(BaseProcess):
    """ Pupil detector for eye video streams. """

    def __init__(self, block=True, **kwargs):
        """ Constructor. """
        from pupil_detectors import Detector2D

        self.detector = Detector2D()

        super().__init__(block=block, **kwargs)

    def _process_packet(self, packet):
        """ Process a new packet. """
        packet.pupil = self.detector.detect(packet.frame)
        packet.broadcasts.append("pupil")
        return packet
