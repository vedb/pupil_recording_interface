import abc
import os

import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.encoder import VideoEncoderFFMPEG
from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.process import BaseProcess, logger
from pupil_recording_interface.utils import get_constructor_args


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
        super().__init__(folder, name=name)

        self.encoder = VideoEncoderFFMPEG(
            self.folder,
            self.name,
            resolution,
            fps,
            color_format,
            codec,
            overwrite=False,
            **(encoder_kwargs or {}),
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

    def write(self, packet):
        """ Write data to disk. """
        self.encoder.write(packet["frame"])

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        self.call(self.write, packet, block=block)

        self._timestamps.append(packet.timestamp)

        return packet

    def stop(self):
        """ Stop the recorder. """
        self.encoder.stop()
        # TODO additionally save timestamps continuously if paranoid=True
        np.save(self.timestamp_file, np.array(self._timestamps))


@process("odometry_recorder", optional=("folder",))
class OdometryRecorder(BaseRecorder):
    """ Recorder for an odometry stream. """

    def __init__(self, folder, name=None, topic="odometry"):
        """ Constructor. """
        super().__init__(folder, name=name)

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

    def write(self, packet):
        """ Write data to disk. """
        self.writer.append(packet["odometry"])

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        self.call(self.write, packet, block=block)

        return packet

    def stop(self):
        """ Stop the recorder. """
        self.writer.close()
