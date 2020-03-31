""""""
import abc
import os

import numpy as np
import cv2

from pupil_recording_interface.config import (
    VideoDisplayConfig,
    VideoRecorderConfig,
)
from pupil_recording_interface.recorder.video import VideoEncoderFFMPEG


class Pipeline(object):
    """ Pipeline for different processing steps. """

    def __init__(self, steps):
        """ Constructor. """
        self.steps = steps

    @classmethod
    def from_config(cls, config, device, folder=None):
        """ Create an instance from a StreamConfig. """
        if config.pipeline is not None:
            steps = []
            for step in config.pipeline:
                # TODO BaseProcess.from_config(step, config, device)
                if isinstance(step, VideoDisplayConfig):
                    steps.append(
                        VideoDisplayProcess(config.name or device.uid)
                    )
                elif isinstance(step, VideoRecorderConfig):
                    steps.append(
                        VideoRecorderProcess(
                            step.folder or folder,
                            step.resolution or device.resolution,
                            step.fps or device.fps,
                            name=config.name or device.uid,
                            color_format=step.color_format
                            or config.color_format,
                            codec=step.codec,
                        )
                    )
                else:
                    raise ValueError(
                        "Unsupported process type: {}".format(type(step))
                    )
            return cls(steps)
        else:
            return None

    def flush(self, data, timestamp):
        """ Flush the pipeline with new data. """
        for step in self.steps:
            data, timestamp = step.process_data_and_timestamp(data, timestamp)

        return data, timestamp

    def stop(self):
        """ Stop the pipeline. """
        for step in self.steps:
            step.stop()


class BaseProcess(object):
    """ Base class for all processes. """

    @abc.abstractmethod
    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """

    def stop(self):
        """ Stop the process. """


class VideoDisplayProcess(BaseProcess):
    """ Display for video stream. """

    def __init__(self, name):
        """ Constructor. """
        self.name = name

    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """
        cv2.imshow(self.name, data)
        cv2.waitKey(1)

        return data, timestamp


class BaseRecorderProcess(BaseProcess):
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


class VideoRecorderProcess(BaseRecorderProcess):
    """ Recorder for a video stream. """

    def __init__(
        self,
        folder,
        resolution,
        fps,
        name=None,
        color_format="bgr24",
        codec="libx264",
        **encoder_kwargs
    ):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        device: BaseVideoDevice
            The device from which to record the video.

        name: str, optional
            The name of the recorder. If not specified, `device.uid` will be
            used.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        encoder_kwargs:
            Addtional keyword arguments passed to the encoder.
        """
        super(VideoRecorderProcess, self).__init__(folder, name=name)

        self.encoder = VideoEncoderFFMPEG(
            self.folder,
            self.name,
            resolution,
            fps,
            color_format,
            codec,
            overwrite=False,
            **encoder_kwargs
        )

        self.timestamp_file = os.path.join(
            self.folder, "{}_timestamps.npy".format(self.name)
        )
        if os.path.exists(self.timestamp_file):
            raise IOError(
                "{} exists, will not overwrite".format(self.timestamp_file)
            )

        self._timestamps = []

    def write(self, frame):
        """ Write data to disk. """
        self.encoder.write(frame)

    def process_data_and_timestamp(self, data, timestamp):
        """ Process data and timestamp. """
        self.write(data)
        # TODO check if this works
        # self._timestamps.append(timestamp)

        return data, timestamp

    def stop(self):
        """ Stop the recorder. """
        self.encoder.stop()
        # TODO additionally save timestamps continuously if paranoid=True
        np.save(self.timestamp_file, np.array(self._timestamps))
