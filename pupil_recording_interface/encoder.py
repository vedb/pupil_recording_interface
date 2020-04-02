import abc
import logging
import os
import socket
import subprocess

import cv2

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
        **kwargs
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
        self.video_file = os.path.join(folder, f"{device_name}.mp4")
        if os.path.exists(self.video_file):
            if overwrite:
                os.remove(self.video_file)
            else:
                raise IOError(
                    f"{self.video_file} exists, will not overwrite"
                )

        self.video_writer = self._init_video_writer(
            self.video_file, codec, color_format, fps, resolution, **kwargs
        )

        # TODO move timestamp writer to BaseStreamRecorder
        self.timestamp_file = os.path.join(
            folder, f"{device_name}_timestamps.npy"
        )
        if os.path.exists(self.timestamp_file) and not overwrite:
            raise IOError(
                f"{self.timestamp_file} exists, will not overwrite"
            )

    @classmethod
    @abc.abstractmethod
    def _init_video_writer(
        cls, video_file, codec, color_format, fps, resolution, **kwargs
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
            f"ffmpeg called with arguments: {' '.join(cmd[1:])}"
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
        size = f"{frame_shape[0]}x{frame_shape[1]}"

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
        try:
            self.video_writer.stdin.write(img.tostring())
        except socket.error:
            # TODO figure out why this is happening in the first place
            pass

    def stop(self):
        """ Stop the encoder. """
        self.video_writer.stdin.write(b"q")
        self.video_writer.wait()
        logger.debug(
            f"Stopped ffmpeg encoder {self.video_writer}"
        )
