""""""
from __future__ import print_function

import os
import abc
import subprocess

import numpy as np
import cv2

from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.device.video import \
    BaseVideoDevice, VideoDeviceUVC, VideoDeviceFLIR
from pupil_recording_interface.recorder import BaseStreamRecorder


class BaseVideoEncoder(object):
    """ Base class for encoder interfaces. """

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', extension='mp4',
                 overwrite=False):
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
        self.video_file = os.path.join(
            folder, '{}.{}'.format(device_name, extension))
        if os.path.exists(self.video_file):
            if overwrite:
                os.remove(self.video_file)
            else:
                raise IOError(
                    '{} exists, will not overwrite'.format(self.video_file))

        self.video_writer = self._init_video_writer(
            self.video_file, codec, color_format, fps, resolution)

        # TODO move timestamp writer to BaseStreamRecorder
        self.timestamp_file = os.path.join(
            folder, '{}_timestamps.npy'.format(device_name))
        if os.path.exists(self.timestamp_file) and not overwrite:
            raise IOError(
                '{} exists, will not overwrite'.format(self.timestamp_file))

    @classmethod
    @abc.abstractmethod
    def _init_video_writer(
            cls, video_file, codec, color_format, fps, resolution):
        """ Init the video writer. """

    @abc.abstractmethod
    def write(self, img):
        """ Write a frame to disk. """


class VideoEncoderOpenCV(BaseVideoEncoder):

    @classmethod
    def _init_video_writer(
            cls, video_file, codec, color_format, fps, resolution):
        """ Init the video writer. """
        codec = cv2.VideoWriter_fourcc(*'MP4V')  # TODO

        return cv2.VideoWriter(
            video_file, codec, fps, resolution, color_format != 'gray')

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

    @classmethod
    def _init_video_writer(
            cls, video_file, codec, color_format, fps, resolution):
        """ Init the video writer. """
        cmd = cls._get_ffmpeg_cmd(
            video_file, resolution[::-1], fps, codec, color_format)

        return subprocess.Popen(cmd, stdin=subprocess.PIPE)

    @classmethod
    def _get_ffmpeg_cmd(
            cls, filename, frame_shape, fps, codec, color_format):
        """ Get the FFMPEG command to start the sub-process. """
        size = '{}x{}'.format(frame_shape[1], frame_shape[0])
        return ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                # -- Input -- #
                '-an',  # no audio
                '-r', str(fps),  # fps
                '-f', 'rawvideo',  # format
                '-s', size,  # resolution
                '-pix_fmt', color_format,  # color format
                '-i', 'pipe:',  # piped to stdin
                # -- Output -- #
                '-c:v', codec,  # video codec
                # '-tune', 'film',  # codec tuning
                filename]

    def write(self, img):
        """ Write a frame to disk.

        Parameters
        ----------
        img : array_like
            The input frame.
        """
        self.video_writer.stdin.write(img.tostring())


class ImageEncoder(BaseVideoEncoder):
    """ Encoder for single images. """

    def __init__(self, *args, **kwargs):
        """ Constructor. """
        super(ImageEncoder, self).__init__(*args, extension='png', **kwargs)
        self._counter = 0

    def _init_video_writer(
            cls, video_file, codec, color_format, fps, resolution):
        """ Init the video writer. """

    def write(self, img):
        """ Write a frame to disk.

        Parameters
        ----------
        img : array_like
            The input frame.
        """
        # get image filename
        folder = os.path.dirname(self.video_file)
        image_file = os.path.split(self.video_file)[-1]
        while os.path.exists(os.path.join(
                folder, '{:03d}_{}'.format(self._counter, image_file))):
            self._counter += 1
        image_file = os.path.join(
            folder, '{:03d}_{}'.format(self._counter, image_file))

        cv2.imwrite(image_file, img)


class VideoRecorder(BaseStreamRecorder):
    """ Recorder for a video stream. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, folder, device, name=None, policy='new_folder',
                 color_format='bgr24', codec='libx264', show_video=False,
                 encoder=None, **kwargs):
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

        encoder: BaseVideoEncoder type, optional
            The encoder class to use for encoding video frames. Can be
            VideoEncoderFFMPEG, VideoEncoderOpenCV or ImageEncoder. Will use
            VideoEncoderFFMPEG by default.
        """
        super(VideoRecorder, self).__init__(
            folder, device, name=name, policy=policy, **kwargs)

        encoder = encoder or VideoEncoderFFMPEG
        self.encoder = encoder(
            self.folder, self.name, self.device.resolution,
            self.device.fps, color_format, codec, overwrite=self.overwrite)

        self.color_format = color_format
        self.show_video = show_video

    @classmethod
    def _from_config(
            cls, config, folder, device=None, encoder=None, overwrite=False):
        """ Create a device from a StreamConfig. """
        # TODO codec and other parameters
        if device is None:
            if config.device_type == 'uvc':
                device = VideoDeviceUVC(
                    config.device_uid, config.resolution, config.fps)
            elif config.device_type == 'flir':
                device = VideoDeviceFLIR(
                    config.device_uid, config.resolution, config.fps)
            elif config.device_type == 't265':
                device = RealSenseDeviceT265(
                    config.device_uid, config.resolution, config.fps,
                    video=config.side)
            else:
                raise ValueError(
                    'Unsupported device type: {}.'.format(config.device_type))

        policy = 'overwrite' if overwrite else 'here'

        return VideoRecorder(
            folder, device, name=config.name, policy=policy, encoder=encoder)

    def start(self):
        """ Start the recorder. """
        self.device.start()

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        # TODO handle uvc.StreamError and reinitialize capture
        # TODO get only jpeg buffer when not showing video
        if self.color_format == 'gray':
            frame, timestamp = self.device._get_frame_and_timestamp('gray')
        else:
            frame, timestamp = self.device._get_frame_and_timestamp()

        # show video if requested and capture key strokes
        # TODO move this to a dedicated method
        if self.show_video:
            # TODO set show_video to false when window is closed
            key = self.device.show_frame(frame)
            if self.event_queue is not None and key > 0:
                self.event_queue.put(key)

        return frame, timestamp

    def write(self, frame):
        """ Write data to disk. """
        if self.recording_event is None or self.recording_event.is_set():
            self.encoder.write(frame)
            # TODO introduce constructor argument whether to clear the event?
            if self.recording_event is not None:
                self.recording_event.clear()

    def stop(self):
        """ Stop the recorder. """
        # TODO additionally save timestamps continuously if paranoid=True
        np.save(self.encoder.timestamp_file, np.array(self._timestamps))
