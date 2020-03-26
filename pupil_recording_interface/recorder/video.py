""""""
import os
import abc
import subprocess
import logging

import numpy as np
import cv2

from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.device.video import (
    VideoDeviceUVC,
    VideoDeviceFLIR,
)
from pupil_recording_interface.recorder import BaseStreamRecorder


logger = logging.getLogger(__name__)


class BaseVideoEncoder(object):
    """ Base class for encoder interfaces. """

    def __init__(
        self,
        folder,
        device_name,
        resolution,
        fps,
        color_format="bgr24",
        codec="libx264",
        overwrite=False,
        **kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        folder: str
            The folder where recorded streams are written to.

        device_name: str
            The name of the video device. The video file will be called
            `name`.mp4.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        overwrite: bool, default False
            If True, overwrite existing video files with the same name.
        """
        self.ffmpeg_counter = 0
        self.video_file = os.path.join(folder, "{}.mp4".format(device_name))
        if os.path.exists(self.video_file):
            if overwrite:
                os.remove(self.video_file)
            else:
                raise IOError(
                    "{} exists, will not overwrite".format(self.video_file)
                )

        self.video_writer = self._init_video_writer(
            self.video_file, codec, color_format, fps, resolution, **kwargs,
        )

        # TODO move timestamp writer to BaseStreamRecorder
        self.timestamp_file = os.path.join(
            folder, "{}_timestamps.npy".format(device_name)
        )
        if os.path.exists(self.timestamp_file) and not overwrite:
            raise IOError(
                "{} exists, will not overwrite".format(self.timestamp_file)
            )

    @classmethod
    @abc.abstractmethod
    def _init_video_writer(
        cls, video_file, codec, color_format, fps, resolution, **kwargs,
    ):
        """ Init the video writer. """

    @abc.abstractmethod
    def write(self, img):
        """ Write a frame to disk. """

    def stop(self):
        """ Stop the encoder. """


class VideoEncoderOpenCV(BaseVideoEncoder):
    """ OpenCV encoder interface. """

    @classmethod
    def _init_video_writer(
        cls, video_file, codec, color_format, fps, resolution, **kwargs
    ):
        """ Init the video writer. """
        codec = cv2.VideoWriter_fourcc(*"MP4V")  # TODO

        return cv2.VideoWriter(
            video_file, codec, fps, resolution, color_format != "gray"
        )

    def write(self, img):
        """ Write a frame to disk.

        Parameters
        ----------
        img : array_like
            The input frame.
        """
        self.video_writer.write(img)


class VideoEncoderFFMPEG(BaseVideoEncoder):
    """ FFMPEG encoder interface. """

    def __init__(
        self,
        folder,
        device_name,
        resolution,
        fps,
        color_format="bgr24",
        codec="libx264",
        overwrite=False,
        preset="ultrafast",
        crf="18",
        flags=None,
    ):
        """ Constructor. """
        super(VideoEncoderFFMPEG, self).__init__(
            folder,
            device_name,
            resolution,
            fps,
            color_format=color_format,
            codec=codec,
            overwrite=overwrite,
            preset=preset,
            crf=crf,
            flags=flags,
        )

    @classmethod
    def _init_video_writer(
        cls,
        video_file,
        codec,
        color_format,
        fps,
        resolution,
        preset="ultrafast",
        crf="18",
        flags=None,
    ):
        """ Init the video writer. """
        # Example for flags: "-profile:v high444 -refs 5"
        cmd = cls._get_ffmpeg_cmd(
            video_file,
            resolution,
            fps,
            codec,
            color_format,
            preset,
            crf,
            flags,
        )
        logger.debug(
            "ffmpeg called with arguments: {}".format(" ".join(cmd[1:]))
        )

        return subprocess.Popen(cmd, stdin=subprocess.PIPE)

    @classmethod
    def _get_ffmpeg_cmd(
        cls,
        filename,
        frame_shape,
        fps,
        codec,
        color_format,
        preset="ultrafast",
        crf="18",
        flags=None,
    ):
        """ Get the FFMPEG command to start the sub-process. """
        size = "{}x{}".format(frame_shape[0], frame_shape[1])

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-an",  # no audio
            "-r",
            str(fps),  # fps
            "-f",
            "rawvideo",  # format
            "-s",
            size,  # resolution
            "-pix_fmt",
            color_format,  # color format
            "-i",
            "pipe:",  # piped to stdin
        ]

        if preset is not None:
            cmd += ["-preset", preset, "-crf", crf]

        if flags is not None:
            cmd += flags.split()

        cmd += ["-c:v", codec, filename]

        return cmd

    def write(self, img):
        """ Write a frame to disk.

        Parameters
        ----------
        img : array_like
            The input frame.
        """
        self.video_writer.stdin.write(img.tostring())

    def stop(self):
        """ Stop the encoder. """
        self.video_writer.stdin.close()


class VideoRecorder(BaseStreamRecorder):
    """ Recorder for a video stream. """

    __metaclass__ = abc.ABCMeta

    def __init__(
        self,
        folder,
        device,
        name=None,
        policy="new_folder",
        color_format="bgr24",
        codec="libx264",
        show_video=False,
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
            The name of the recorder. If not specified, `device.uid` will be
            used.

        policy: str, default 'new_folder'
            Policy for recording folder creation. If 'new_folder',
            new sub-folders will be created with incremental numbering. If
            'here', the data will be recorded to the specified folder but
            will throw an error when existing files would be overwritten. If
            'overwrite', the data will be recorded to the specified folder
            and existing files will possibly overwritten.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        show_video: bool, default False,
            If True, show the video stream in a window.

        encoder_kwargs:
            Addtional keyword arguments passed to the encoder.
        """
        super(VideoRecorder, self).__init__(
            folder, device, name=name, policy=policy
        )

        self.encoder = VideoEncoderFFMPEG(
            self.folder,
            self.name,
            self.device.resolution,
            self.device.fps,
            color_format,
            codec,
            self.overwrite,
            **encoder_kwargs,
        )

        self.color_format = color_format
        self.show_video = show_video

    @classmethod
    def _from_config(cls, config, folder, device=None, overwrite=False):
        """ Create a device from a StreamConfig. """
        # TODO codec and other parameters
        if device is None:
            if config.device_type == "uvc":
                device = VideoDeviceUVC(
                    config.device_uid, config.resolution, config.fps
                )
            elif config.device_type == "flir":
                device = VideoDeviceFLIR(
                    config.device_uid, config.resolution, config.fps
                )
            elif config.device_type == "t265":
                device = RealSenseDeviceT265(
                    config.device_uid,
                    config.resolution,
                    config.fps,
                    video=config.side,
                )
            else:
                raise ValueError(
                    "Unsupported device type: {}.".format(config.device_type)
                )

        policy = "overwrite" if overwrite else "here"

        return VideoRecorder(folder, device, name=config.name, policy=policy)

    def start(self):
        """ Start the recorder. """
        self.device.start()

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        # TODO handle uvc.StreamError and reinitialize capture
        # TODO get only jpeg buffer when not showing video
        if self.color_format == "gray":
            frame, timestamp = self.device._get_frame_and_timestamp("gray")
        else:
            frame, timestamp = self.device._get_frame_and_timestamp()

        # show video if requested
        if self.show_video:
            # TODO set show_video to false when window is closed
            self.device.show_frame(frame)

        return frame, timestamp

    def write(self, frame):
        """ Write data to disk. """
        self.encoder.write(frame)

    def stop(self):
        """ Stop the recorder. """
        # TODO additionally save timestamps continuously if paranoid=True
        self.encoder.stop()
        np.save(self.encoder.timestamp_file, np.array(self._timestamps))
