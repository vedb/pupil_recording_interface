import abc
import os
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.encoder import VideoEncoderFFMPEG
from pupil_recording_interface.utils import get_constructor_args

logger = logging.getLogger(__name__)


class BaseProcess:
    """ Base class for all processes. """

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
        assert process.registry[config.process_type] is cls

        cls_kwargs = get_constructor_args(cls, config, **kwargs)

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process"""

    @abc.abstractmethod
    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """

    def stop(self):
        """ Stop the process. """


@process("video_display")
class VideoDisplay(BaseProcess):
    """ Display for video stream. """

    def __init__(self, name):
        """ Constructor. """
        self.name = name

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        return cls(stream_config.name or device.device_uid)

    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """
        cv2.imshow(self.name, data)
        cv2.waitKey(1)

        return data, timestamp


class BaseRecorder(BaseProcess):
    """ Recorder for stream. """

    def __init__(self, folder, name=None):
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
        return cls(
            config.folder or kwargs.get("folder", None),
            config.resolution or device.resolution,
            config.fps or device.fps,
            name=stream_config.name or device.device_uid,
            color_format=config.color_format or stream_config.color_format,
            codec=config.codec,
        )

    def write(self, frame):
        """ Write data to disk. """
        self.encoder.write(frame)

    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """
        self.write(data)
        # TODO check if this works
        self._timestamps.append(timestamp)

        return data, timestamp

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

    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """
        self.write(data)

        return data, timestamp

    def stop(self):
        """ Stop the recorder. """
        self.writer.close()


@process("pupil_detector")
class PupilDetector(BaseProcess):
    """ Pupil detector for eye video streams. """

    def __init__(self, overlay=False):
        """ Constructor. """
        self.overlay = overlay

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        return cls(config.overlay)

    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """
        from pupil_detectors import Detector2D

        detector = Detector2D()
        result = detector.detect(data)

        if self.overlay:
            data = cv2.cvtColor(data, cv2.COLOR_GRAY2BGR)
            ellipse = result["ellipse"]
            cv2.ellipse(
                data,
                tuple(int(v) for v in ellipse["center"]),
                tuple(int(v / 2) for v in ellipse["axes"]),
                ellipse["angle"],
                0,
                360,  # start/end angle for drawing
                (0, 0, 255),  # color (BGR): red
            )

        return data, timestamp
