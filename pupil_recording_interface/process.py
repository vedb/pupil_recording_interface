import abc
import os
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.encoder import VideoEncoderFFMPEG

logger = logging.getLogger(__name__)


class BaseProcess(object):
    """ Base class for all processes. """

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
            The name of the legacy.
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
            The name of the legacy. If not specified, `device.uid` will be
            used.

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
        """ Stop the legacy. """
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

    def start(self):
        """ Start the legacy. """
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
        """ Stop the legacy. """
        self.writer.close()
