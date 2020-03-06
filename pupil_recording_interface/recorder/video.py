""""""
from __future__ import print_function

import os
import abc
import subprocess

import numpy as np
import cv2

from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.device.video import \
     VideoDeviceUVC, VideoDeviceFLIR
from pupil_recording_interface.recorder import BaseStreamRecorder


class BaseVideoEncoder(object):
    """ Base class for encoder interfaces. """

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', overwrite=False,
                 preset='ultrafast', crf='18'):
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
        # print('Base Codec: ', codec)
        self.ffmpeg_counter = 0
        self.video_file = os.path.join(folder, '{}.mp4'.format(device_name))
        if os.path.exists(self.video_file):
            if overwrite:
                os.remove(self.video_file)
            else:
                raise IOError(
                    '{} exists, will not overwrite'.format(self.video_file))

        self.video_writer = self._init_video_writer(
            self.video_file, codec, color_format, fps, resolution, preset, crf)

        # TODO move timestamp writer to BaseStreamRecorder
        self.timestamp_file = os.path.join(
            folder, '{}_timestamps.npy'.format(device_name))
        if os.path.exists(self.timestamp_file) and not overwrite:
            raise IOError(
                '{} exists, will not overwrite'.format(self.timestamp_file))

    @classmethod
    @abc.abstractmethod
    def _init_video_writer(
            cls, video_file, codec, color_format, fps, resolution,
            preset='ultrafast', crf='18'):
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


# Stub, for maybe.
# class HDFEncoder(BaseVideoEncoder):
#     """Not actually an encoder, just writing to hdf file"""
#     def __init__(self, *args):
#         # Lazy import of h5py at class initialization
#         import h5py
#         self.idx = 0
#         super(self.__init__)

#     @classmethod
#     def _init_video_writer(
#         cls, video_file, codec, color_format, fps, resolution):
#         """Init the h5py object"""
#         # Get resolution
#         resx, resy = resolution
#         # bastardizing inputs in uninterpretable fashion
#         mins = color_format
#         n = fps * 60 * mins
#         if codec is not None:
#             copts = dict(compression_opts=codec)
#         else:
#             copts = {}
#         # Create HDF file
#         writer = h5py.File(video_file, mode='rb')
#         # Pre-allocate dataset(s?)
#         # Dataset for video
#         writer.create_dataset('video', shape=(resx, resy, 3, n),
#                           dtype=np.uint8, compression=compression, **copts)
#         # Dataset for time?
#         #writer.create_dataset('time', shape=(n,), dtype=np.float32)
#         return writer
#     def write(self, img):
#         self.video_writer['video'][:, :, :, self.idx] = img
#         #self['time'][self.idx] = time.time() # or, however this is done
#         self.idx += 1

class VideoEncoderFFMPEG(BaseVideoEncoder):
    """ FFMPEG encoder interface. """

    @classmethod
    def _init_video_writer(
            cls, video_file, codec, color_format, fps, resolution,
            preset='ultrafast', crf='18'):
        """ Init the video writer. """
        cmd = cls._get_ffmpeg_cmd(
            video_file, resolution[::-1], fps, codec, color_format, preset,
            crf)  # [::-1]
        print('FFMPEG_cmd:', cmd)

        return subprocess.Popen(cmd, stdin=subprocess.PIPE)

    @classmethod
    def _get_ffmpeg_cmd(
            cls, filename, frame_shape, fps, codec, color_format,
            preset='ultrafast', crf='18'):
        """ Get the FFMPEG command to start the sub-process. """
        size = '{}x{}'.format(frame_shape[0], frame_shape[1])
        print('codec:size ', size)
        if (preset == 'None'):
            return ['ffmpeg',  # '-hide_banner', '-loglevel', 'error',
                    # -- Input -- #
                    '-an',  # no audio
                    '-r', str(fps),  # fps
                    '-f', 'rawvideo',  # format
                    '-s', size,  # resolution
                    '-pix_fmt', color_format,  # color format
                    '-i', 'pipe:',  # piped to stdin
                    # '-preset', preset,
                    # '-profile:v', 'high444',
                    # '-refs', '5',
                    # '-crf', crf,
                    # -- Output -- #
                    '-c:v', codec,  # video codec
                    # '-tune', 'film',  # codec tuning
                    filename]
        elif (size == 'crazy_large'):  # TODO: CLean up this, only for test
            return ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                    # -- Input -- #
                    '-an',  # no audio
                    '-r', str(fps),  # fps
                    '-f', 'rawvideo',  # format
                    '-s', size,  # resolution
                    '-pix_fmt', color_format,  # color format
                    '-i', 'pipe:',  # piped to stdin
                    '-preset', preset,
                    # '-profile:v', 'high444',
                    # '-refs', '5',
                    '-vf', 'scale=1280:720',
                    '-crf', crf,
                    # -- Output -- #
                    '-c:v', codec,  # video codec
                    # '-tune', 'film',  # codec tuning
                    filename]
        else:
            return ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                    # -- Input -- #
                    '-an',  # no audio
                    '-r', str(fps),  # fps
                    '-f', 'rawvideo',  # format
                    '-s', size,  # resolution
                    '-pix_fmt', color_format,  # color format
                    '-i', 'pipe:',  # piped to stdin
                    '-preset', preset,
                    # '-profile:v', 'high444',
                    # '-refs', '5',
                    '-crf', crf,
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
        # print('write image', img.shape)
        self.video_writer.stdin.write(img.tostring())
        # np.savez('/home/veddy/Videos/FLIR_images/capture_3/frame_'+str(self.ffmpeg_counter),img)
        # self.ffmpeg_counter = self .ffmpeg_counter + 1
        # self.video_writer.write(img)


class VideoRecorder(BaseStreamRecorder):
    """ Recorder for a video stream. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, folder, device, name=None, policy='new_folder',
                 color_format='bgr24', codec='libx264', show_video=False,
                 **kwargs):
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
        """
        super(VideoRecorder, self).__init__(
            folder, device, name=name, policy=policy, **kwargs)

        # print('Codec: ', codec)

        self.encoder = VideoEncoderFFMPEG(
            self.folder, self.name, self.device.resolution,
            self.device.fps, color_format, codec, self.overwrite)

        self.color_format = color_format
        self.show_video = show_video

    @classmethod
    def _from_config(cls, config, folder, device=None, overwrite=False):
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
            folder, device, name=config.name, policy=policy)

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
        np.save(self.encoder.timestamp_file, np.array(self._timestamps))
        self.encoder.video_writer.stdin.close()
