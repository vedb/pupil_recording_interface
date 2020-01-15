""""""
from __future__ import print_function

import os
import subprocess
import multiprocessing as mp
import time
from abc import ABCMeta
from collections import namedtuple, deque

import numpy as np

from pupil_recording_interface.device.video import \
    BaseVideoDevice, VideoDeviceUVC, VideoDeviceFLIR
from pupil_recording_interface.recorder import BaseRecorder


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

        # TODO set format='gray' for eye cameras
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


class BaseVideoCapture(BaseVideoDevice, VideoEncoder):
    """ Base class for all video captures. """

    __metaclass__ = ABCMeta

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', aliases=None,
                 overwrite=False, show_video=False):
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
        """
        BaseVideoDevice.__init__(
            self, device_name, resolution, fps, aliases, init_capture=False)
        VideoEncoder.__init__(
            self, folder, device_name, resolution, fps, color_format, codec,
            overwrite)

        self.color_format = color_format
        self.show_video = show_video

        self._last_timestamp = 0.
        self._fps_buffer = deque(maxlen=100)
        self.flir_camera = None

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return 0.
        else:
            return np.nanmean(self._fps_buffer)

    def run(self, stop_event=None, fps_queue=None):
        """ Start the recording.

        Parameters
        ----------
        stop_event: multiprocessing.Event, optional
            An event that stops recording in a multi-threaded setting.

        fps_queue: multiprocessing.Queue, optional
            A queue for the current fps in a multi-threaded setting.
        """
        # TODO uvc capture has to be initialized here for multi-threaded
        #  operation, check if we can circumvent this, e.g. with spawn()
        self.capture = self._get_capture(
            self.device_name, self.resolution, self.fps)

        timestamps = []

        while True:
            try:
                if stop_event is not None and stop_event.is_set():
                    break

                # TODO handle uvc.StreamError and reinitialize capture
                if self.color_format == 'gray':
                    frame, timestamp = self._get_frame_and_timestamp('gray')
                else:
                    # TODO: Hacky way to pass the FLIR Camera object
                    frame, timestamp = self._get_frame_and_timestamp(self.flir_camera)

                # encode video frame
                self.write(frame)

                # save timestamp and fps
                timestamps.append(timestamp)

                if timestamp != self._last_timestamp:
                    fps = 1. / (timestamp - self._last_timestamp)
                else:
                    fps = np.nan

                if fps_queue is not None:
                    fps_queue.put(fps)
                else:
                    self._fps_buffer.append(fps)

                self._last_timestamp = timestamp

                # show video if requested
                if self.show_video:
                    # TODO set show_video to false when window is closed
                    self.show_frame(frame)

            except KeyboardInterrupt:
                break

        np.save(self.timestamp_file, np.array(timestamps))


class VideoCaptureUVC(BaseVideoCapture, VideoDeviceUVC):
    """ Video capture for UVC devices. """


class VideoCaptureFLIR(BaseVideoCapture, VideoDeviceFLIR):
    """ Video capture for FLIR devices. """


class VideoRecorder(BaseRecorder):
    """ Recorder for multiple video streams. """

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
        self.captures = self._init_captures(
            self.folder, configs, aliases, show_video)
        self.quiet = quiet

        self._stdout_delay = 3.  # delay before showing fps on stdout
        self._max_queue_size = 20  # max size of process fps queue

    @classmethod
    def _init_captures(cls, folder, configs, aliases, show_video):
        """ Init VideoCapture instances for all configs. """
        captures = {}
        for c in configs:
            if c.device_type == 'uvc':
                # TODO VideoCapture.from_config()?
                captures[c.device_name] = VideoCaptureUVC(
                    folder, c.device_name, c.resolution, c.fps, c.color_format,
                    aliases=aliases, show_video=show_video)
            elif c.device_type == 'flir':
                captures[c.device_name] = VideoCaptureFLIR(
                    folder, c.device_name, c.resolution, c.fps, c.color_format,
                    aliases=aliases, show_video=show_video)
            else:
                raise ValueError(
                    'Unsupported device type: {}.'.format(c.device_type))

        return captures

    @classmethod
    def _init_processes(cls, captures, max_queue_size):
        """ Create one process for each VideoCapture instance. """
        stop_event = mp.Event()
        queues = {
            c_name: mp.Queue(maxsize=max_queue_size)
            for c_name in captures.keys()}
        processes = {
            c_name:
                mp.Process(target=c.run, args=(stop_event, queues[c_name]))
            for c_name, c in captures.items()}

        return processes, queues, stop_event

    @classmethod
    def _start_processes(cls, processes):
        """ Start all capture processes. """
        for process in processes.values():
            process.start()

    @classmethod
    def _stop_processes(cls, processes, stop_event):
        """ Stop all capture processes. """
        stop_event.set()
        for process in processes.values():
            process.join()

    def run(self):
        """ Start the recording. """
        if not self.quiet:
            print('Started recording to {}'.format(self.folder))

        processes, queues, stop_event = self._init_processes(
            self.captures, self._max_queue_size)
        self._start_processes(processes)

        start_time = time.time()

        while True:
            try:
                # get fps from queues
                for capture_name, capture in self.captures.items():
                    while not queues[capture_name].empty():
                        capture._fps_buffer.append(queues[capture_name].get())

                # display fps after self._stdout_delay seconds
                if not self.quiet \
                        and time.time() - start_time > self._stdout_delay:
                    f_strs = ', '.join(
                        '{}: {:.2f} Hz'.format(c_name, c.current_fps)
                        for c_name, c in self.captures.items())
                    print('\rSampling rates: ' + f_strs, end='')

            except KeyboardInterrupt:
                self._stop_processes(processes, stop_event)
                break

        if not self.quiet:
            print('\nStopped recording')
