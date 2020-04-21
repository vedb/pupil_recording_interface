import abc
import os
from collections import deque

import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.encoder import VideoEncoderFFMPEG
from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.process import BaseProcess, logger


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


@process(
    "video_recorder", optional=("folder", "resolution", "fps", "color_format")
)
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
        encoder_kwargs=None,
        source_timestamps=True,
        **kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        resolution: tuple, len 2
            Resolution of the recorded video.

        fps: int
            Frame rate of the recorded video.

        name: str, optional
            The name of the recorder. If not specified, `device.device_uid`
            will be used.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        encoder_kwargs: dict
            Addtional keyword arguments passed to the encoder.
        """
        self.fps = fps
        self.resolution = resolution
        self.color_format = color_format
        self.codec = codec
        self.encoder_kwargs = encoder_kwargs
        self.source_timestamps = source_timestamps

        super().__init__(folder, name=name, **kwargs)

        self.encoder = None
        self.writer = None

        self.timestamp_file = os.path.join(
            self.folder, f"{self.name}_timestamps.npy"
        )
        if os.path.exists(self.timestamp_file):
            raise IOError(f"{self.timestamp_file} exists, will not overwrite")

        self._timestamps = deque()

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config,
            folder=config.folder or kwargs.get("folder", None),
            resolution=config.resolution or device.resolution,
            fps=config.fps or device.fps,
            name=stream_config.name or device.device_uid,
            color_format=config.color_format or stream_config.color_format,
        )

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process. """
        self.encoder = VideoEncoderFFMPEG(
            self.folder,
            self.name,
            self.resolution,
            self.fps,
            self.color_format,
            self.codec,
            overwrite=False,
            **(self.encoder_kwargs or {}),
        )

        if self.source_timestamps:
            self.writer = PLData_Writer(self.folder, self.name)

    def write(self, packet):
        """ Write data to disk. """
        self.encoder.write(packet["frame"])

        if self.writer is not None:
            self.writer.append(
                {
                    "topic": self.name,
                    "timestamp": packet.timestamp,
                    "source_timestamp": packet.source_timestamp,
                }
            )

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        self.call(self.write, packet, block=block)

        self._timestamps.append(packet.timestamp)

        return packet

    def stop(self):
        """ Stop the recorder. """
        self.encoder.stop()
        self.encoder = None
        np.save(self.timestamp_file, np.array(self._timestamps))

        if self.writer is not None:
            self.writer.file_handle.close()
            self.writer = None


@process("motion_recorder", optional=("folder", "motion_type"))
class MotionRecorder(BaseRecorder):
    """ Recorder for a motion stream. """

    def __init__(self, folder, motion_type, name=None, **kwargs):
        """ Constructor. """
        self.motion_type = motion_type
        self.topic = name or motion_type

        super().__init__(folder, name=name, **kwargs)

        self.filename = os.path.join(self.folder, self.topic + ".pldata")
        if os.path.exists(self.filename):
            raise IOError(f"{self.filename} exists, will not overwrite")
        self.writer = PLData_Writer(self.folder, self.topic)

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config,
            folder=config.folder or kwargs.get("folder", None),
            motion_type=stream_config.motion_type,
        )

        return cls(**cls_kwargs)

    def start(self):
        """ Start the recorder. """
        logger.debug(f"Started motion recorder, recording to {self.filename}")

    def write(self, packet):
        """ Write data to disk. """
        try:
            self.writer.append(packet[self.motion_type])
        except KeyError:
            logger.warning(f"Packet missing expected data: {self.motion_type}")

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        self.call(self.write, packet, block=block)

        return packet

    def stop(self):
        """ Stop the recorder. """
        self.writer.close()
