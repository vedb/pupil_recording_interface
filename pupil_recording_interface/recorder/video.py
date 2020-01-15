""""""
from __future__ import print_function

import os
import abc
import subprocess
import multiprocessing as mp
import time
from collections import namedtuple, deque

import numpy as np

from pupil_recording_interface.device.realsense import VideoDeviceT265
from pupil_recording_interface.device.video import \
    BaseVideoDevice, VideoDeviceUVC, VideoDeviceFLIR
from pupil_recording_interface.recorder import BaseRecorder, BaseStreamRecorder

# TODO StreamConfig class
VideoConfig = namedtuple(
    'VideoConfig', [
        'device_type', 'device_name', 'resolution', 'fps', 'color_format'])
# defaults apply from right to left, so we only set a default parameter for
# color_format
VideoConfig.__new__.__defaults__ = ('bgr24',)


class VideoEncoder(object):
    """ FFMPEG encoder interface. """

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', overwrite=False):
        """ Constructor.

        Parameters
        ----------
        folder: str
            The folder where recorded streams are written to.

        device_name: str
            The name of the video device. For UVC devices, this corresponds
            to the ``'name'`` field of the items obtained through
            ``uvc.get_device_list()``. Can also be a key of `aliases`. The
            name of the video file will be `device_name`.mp4.

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
        # ffmpeg pipe
        self.video_file = os.path.join(folder, '{}.mp4'.format(device_name))
        if os.path.exists(self.video_file):
            if overwrite:
                os.remove(self.video_file)
            else:
                raise IOError(
                    '{} exists, will not overwrite'.format(self.video_file))

        cmd = self._get_ffmpeg_cmd(
            self.video_file, resolution[::-1], fps, codec, color_format)
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        # timestamp writer
        self.timestamp_file = os.path.join(
            folder, '{}_timestamps.npy'.format(device_name))
        if os.path.exists(self.timestamp_file) and not overwrite:
            raise IOError(
                '{} exists, will not overwrite'.format(self.timestamp_file))

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
                '-tune', 'film',  # codec tuning
                filename]

    def write(self, img):
        """ Pipe a frame to the FFMPEG subprocess.

        Parameters
        ----------
        img : array_like
            The input frame.
        """
        self.process.stdin.write(img.tostring())


class BaseVideoRecorder(BaseVideoDevice, BaseStreamRecorder):
    """ Base class for all video recorders. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', aliases=None,
                 overwrite=False, show_video=False, init_capture=False,
                 **kwargs):
        """ Constructor.

        Parameters
        ----------
        folder: str
            The folder where recorded streams are written to.

        device_name: str
            The name of the video device. For UVC devices, this corresponds
            to the ``'name'`` field of the items obtained through
            ``uvc.get_device_list()``. Can also be a key of `aliases`. The
            name of the video file will be `device_name`.mp4.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        aliases: dict, optional
            A mapping from aliases to valid device names. See `device_name`.

        overwrite: bool, default False
            If True, overwrite existing video files with the same name.

        show_video: bool, default False,
            If True, show the video stream in a window.

        init_capture: bool, default True
            If True, initialize the underlying capture upon construction.
            Set to False for multi-threaded recording.
        """
        super(BaseVideoRecorder, self).__init__(
            device_name, resolution, fps, aliases=aliases,
            init_capture=init_capture, **kwargs)

        self.encoder = VideoEncoder(
            folder, device_name, resolution, fps, color_format, codec,
            overwrite)

        self.color_format = color_format
        self.show_video = show_video

        self._timestamps = []
        self._last_timestamp = 0.
        self._fps_buffer = deque(maxlen=100)

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return 0.
        else:
            return np.nanmean(self._fps_buffer)

    def init_capture(self):
        """ Initialize the underlying capture. """
        self.capture = self._get_capture(
            self.device_name, self.resolution, self.fps, **self.capture_kwargs)

    def run_post_recording_hooks(self):
        """ Hooks to run after the main recording loop. """
        # TODO additionally save timestamps continuously if paranoid=True
        np.save(self.encoder.timestamp_file, np.array(self._timestamps))

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        # TODO handle uvc.StreamError and reinitialize capture
        if self.color_format == 'gray':
            frame, timestamp = self._get_frame_and_timestamp('gray')
        else:
            frame, timestamp = self._get_frame_and_timestamp()

        # show video if requested
        if self.show_video:
            # TODO set show_video to false when window is closed
            self.show_frame(frame)

        return frame, timestamp

    def write(self, frame):
        """ Write data to disk. """
        self.encoder.write(frame)


class VideoRecorderUVC(BaseVideoRecorder, VideoDeviceUVC):
    """ Video recorder for UVC devices. """


class VideoRecorderFLIR(BaseVideoRecorder, VideoDeviceFLIR):
    """ Video recorder for FLIR devices. """


class VideoRecorderT265(BaseVideoRecorder, VideoDeviceT265):
    """ Video recorder for RealSense T265 devices. """


class VideoRecorder(BaseRecorder):
    """ Recorder for multiple video streams. """
    # TODO refactor into MultiStreamRecorder

    def __init__(self, folder, configs, aliases=None, quiet=False,
                 show_video=False):
        """ Constructor.

        Parameters
        ----------
        folder: str
            The folder where recorded streams are written to.

        configs: iterable of pupil_recording_interface.VideoConfig
            An iterable of video device configurations.

        aliases: dict, optional
            A mapping from aliases to valid device names. See `device_name`.

        quiet: bool, default False,
            If True, do not print infos to stdout.

        show_video: bool, default False,
            If True, show the video stream in a window.
        """
        super(VideoRecorder, self).__init__(folder)
        self.recorders = self._init_recorders(
            self.folder, configs, aliases, show_video)
        self.quiet = quiet

        self._stdout_delay = 3.  # delay before showing fps on stdout
        self._max_queue_size = 20  # max size of process fps queue

    @classmethod
    def _init_recorders(cls, folder, configs, aliases, show_video):
        """ Init VideoCapture instances for all configs. """
        recorders = {}
        for c in configs:
            # TODO VideoRecorder.from_config()
            if c.device_type == 'uvc':
                recorders[c.device_name] = VideoRecorderUVC(
                    folder, c.device_name, c.resolution, c.fps, c.color_format,
                    aliases=aliases, show_video=show_video)
            elif c.device_type == 'flir':
                recorders[c.device_name] = VideoRecorderFLIR(
                    folder, c.device_name, c.resolution, c.fps, c.color_format,
                    aliases=aliases, show_video=show_video)
            elif c.device_type == 't265':
                # init_capture=True because the realsense pipeline ("capture")
                # can be started in this same thread
                recorders[c.device_name] = VideoRecorderT265(
                    folder, c.device_name, c.resolution, c.fps, c.color_format,
                    aliases=aliases, show_video=show_video, init_capture=True)
            else:
                raise ValueError(
                    'Unsupported device type: {}.'.format(c.device_type))

        return recorders

    @classmethod
    def _init_processes(cls, recorders, max_queue_size):
        """ Create one process for each VideoCapture instance. """
        # TODO one recorder may need multiple processes & queues
        stop_event = mp.Event()
        queues = {
            c_name: mp.Queue(maxsize=max_queue_size)
            for c_name in recorders.keys()}
        processes = {
            c_name:
                mp.Process(target=c.run, args=(stop_event, queues[c_name]))
            for c_name, c in recorders.items()}

        return processes, queues, stop_event

    @classmethod
    def _start_processes(cls, processes):
        """ Start all recorder processes. """
        for process in processes.values():
            process.start()

    @classmethod
    def _stop_processes(cls, processes, stop_event):
        """ Stop all recorder processes. """
        stop_event.set()
        for process in processes.values():
            process.join()

    def run(self):
        """ Start the recording. """
        if not self.quiet:
            print('Started recording to {}'.format(self.folder))

        processes, queues, stop_event = self._init_processes(
            self.recorders, self._max_queue_size)
        self._start_processes(processes)

        start_time = time.time()

        while True:
            try:
                # get fps from queues
                for recorder_name, recorder in self.recorders.items():
                    while not queues[recorder_name].empty():
                        recorder._fps_buffer.append(
                            queues[recorder_name].get())

                # display fps after self._stdout_delay seconds
                if not self.quiet \
                        and time.time() - start_time > self._stdout_delay:
                    f_strs = ', '.join(
                        '{}: {:.2f} Hz'.format(c_name, c.current_fps)
                        for c_name, c in self.recorders.items())
                    print('\rSampling rates: ' + f_strs, end='')

            except KeyboardInterrupt:
                self._stop_processes(processes, stop_event)
                break

        if not self.quiet:
            print('\nStopped recording')
