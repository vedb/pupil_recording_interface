""""""
from __future__ import print_function

import os
import abc
import subprocess
import multiprocessing as mp
import time

import numpy as np

from pupil_recording_interface.device.realsense import VideoDeviceT265
from pupil_recording_interface.device.video import \
    BaseVideoDevice, VideoDeviceUVC, VideoDeviceFLIR
from pupil_recording_interface.recorder import BaseRecorder, BaseStreamRecorder


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
            name of the video file will be `name`.mp4.

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


class BaseVideoRecorder(BaseStreamRecorder):
    """ Base class for all video recorders. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, folder, device, name=None, policy='new_folder',
                 color_format='bgr24', codec='libx264', show_video=False,
                 **kwargs):
        """ Constructor.

        Parameters
        ----------
        folder: str
            The folder where recorded streams are written to.

        device: BaseVideoDevice

        codec: str, default 'libx264'
            The desired video codec.

        show_video: bool, default False,
            If True, show the video stream in a window.
        """
        super(BaseVideoRecorder, self).__init__(
            folder, device, name=name, policy=policy, **kwargs)

        self.encoder = VideoEncoder(
            self.folder, self.name, self.device.resolution,
            self.device.fps, color_format, codec, self.overwrite)

        self.color_format = color_format
        self.show_video = show_video

    @classmethod
    def from_config(cls, config, folder):
        """ Create a device from a StreamConfig. """
        # TODO codec and other parameters
        if config.device_type == 'uvc':
            device = VideoDeviceUVC(
                config.device_uid, config.resolution, config.fps, start=False)
        elif config.device_type == 'flir':
            device = VideoDeviceFLIR(
                config.device_uid, config.resolution, config.fps, start=False)
        elif config.device_type == 't265':
            # start=True because the realsense pipeline ("capture")
            # can be started in this same thread
            device = VideoDeviceT265(
                config.device_uid, config.resolution, config.fps, start=True)
        else:
            raise ValueError(
                'Unsupported device type: {}.'.format(config.device_type))

        return BaseVideoRecorder(
            folder, device, name=config.name, policy='here')

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return 0.
        else:
            return np.nanmean(self._fps_buffer)

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


class VideoRecorder(BaseRecorder):
    """ Recorder for multiple video streams. """
    # TODO refactor into MultiStreamRecorder

    def __init__(self, folder, configs, quiet=False, show_video=False):
        """ Constructor.

        Parameters
        ----------
        folder: str
            The folder where recorded streams are written to.

        configs: iterable of pupil_recording_interface.VideoStreamConfig
            An iterable of video device configurations.

        quiet: bool, default False,
            If True, do not print infos to stdout.

        show_video: bool, default False,
            If True, show the video stream in a window.
        """
        super(VideoRecorder, self).__init__(folder)
        self.recorders = self._init_recorders(self.folder, configs, show_video)
        self.quiet = quiet

        self._stdout_delay = 3.  # delay before showing fps on stdout
        self._max_queue_size = 20  # max size of process fps queue

    @classmethod
    def _init_recorders(cls, folder, configs, show_video):
        """ Init VideoCapture instances for all configs. """
        recorders = {}
        for config in configs:
            recorder = BaseVideoRecorder.from_config(config, folder)
            recorder.show_video = show_video
            recorders[config.name] = recorder

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
