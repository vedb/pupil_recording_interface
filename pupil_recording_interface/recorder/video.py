""""""
import os
import multiprocessing as mp
import time
from collections import namedtuple, deque

import numpy as np

import uvc
import cv2

from pupil_recording_interface.recorder import BaseRecorder


VideoConfig = namedtuple(
    'VideoConfig', ['device_name', 'resolution', 'fps', 'color_format'])
# defaults apply from right to left, so we only set a default parameter for
# color_format
VideoConfig.__new__.__defaults__ = ('bgr24',)


class VideoEncoder(object):

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', overwrite=False):
        """"""
        import subprocess

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
        return ['ffmpeg', '-hide_banner', '-loglevel', 'panic', '-r', str(fps),
                '-an', '-f', 'rawvideo', '-s', size, '-pix_fmt', color_format,
                '-i', 'pipe:', '-c:v', codec, filename]

    def write(self, img):
        """"""
        self.process.stdin.write(img.tostring())


class VideoDevice(object):

    # TODO make these configurable
    _aliases = {
        'eye0': 'Pupil Cam1 ID0',
        'eye1': 'Pupil Cam1 ID1',
        'world': 'Pupil Cam1 ID2',
    }

    def __init__(self, device_name, resolution, fps, init_capture=True):
        """"""
        if device_name in self._aliases:
            device_name = self._aliases[device_name]

        self.device_name = device_name
        self.resolution = resolution
        self.fps = fps

        if init_capture:
            self.capture = self._get_capture(device_name, resolution, fps)
        else:
            self.capture = None

    @classmethod
    def _get_connected_device_uids(cls):
        """ Get a mapping from devices names to UIDs. """
        return {
            device['name']: device['uid'] for device in uvc.device_list()}

    @classmethod
    def _get_device_uid(cls, device_name):
        """ Get the UID for a device by name. """
        try:
            return cls._get_connected_device_uids()[device_name]
        except KeyError:
            raise ValueError(
                'Device with name {} not connected.'.format(device_name))

    @classmethod
    def _get_available_modes(cls, device_uid):
        """ Get the available modes for a device by UID. """
        return uvc.Capture(device_uid).avaible_modes  # [sic]

    @classmethod
    def _get_controls(cls, device_uid):
        """ Get the current controls for a device by UID. """
        return {
            c.display_name: c.value for c in uvc.Capture(device_uid).controls}

    @classmethod
    def _get_capture(cls, device_name, resolution, fps):
        """ Get a capture instance for a device by name. """
        device_uid = cls._get_device_uid(device_name)

        # verify selected mode
        if resolution + (fps,) not in cls._get_available_modes(device_uid):
            raise ValueError('Unsupported frame mode: {}x{}@{}fps.'.format(
                resolution[0], resolution[1], fps))

        capture = uvc.Capture(device_uid)
        capture.frame_mode = resolution + (fps,)

        return capture

    @classmethod
    def _get_timestamp(cls):
        """ Get the current monotonic time from the UVC backend. """
        return uvc.get_time_monotonic()

    @property
    def device_uid(self):
        """ The UID of this device. """
        return self._get_device_uid(self.device_name)

    @property
    def available_modes(self):
        """ Available frame modes for this device. """
        if self.capture is None:
            return self._get_available_modes(self.device_uid)
        else:
            return self.capture.avaible_modes  # [sic]

    @property
    def controls(self):
        """ Current controls for this device. """
        if self.capture is None:
            return self._get_controls(self.device_uid)
        else:
            return {c.display_name: c.value for c in self.capture.controls}

    def get_raw_frame(self, robust=False):
        """"""
        if robust:
            frame = self.capture.get_frame_robust()
        else:
            frame = self.capture.get_frame()

        return frame.img

    def show_frame(self, frame):
        """"""
        cv2.imshow(self.device_name, frame)
        return cv2.waitKey(1)


class VideoCapture(VideoEncoder, VideoDevice):

    def __init__(self, folder, device_name, resolution, fps,
                 color_format='bgr24', codec='libx264', overwrite=False,
                 show_video=False):
        """"""
        VideoDevice.__init__(self, device_name, resolution, fps,
                             init_capture=False)
        VideoEncoder.__init__(self, folder, device_name, resolution, fps,
                              color_format, codec, overwrite)

        self.color_format = color_format
        self.show_video = show_video

        self._last_timestamp = 0.
        self._fps_buffer = deque(maxlen=100)

    @property
    def current_fps(self):
        """"""
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return 0.
        else:
            return np.nanmean(self._fps_buffer)

    def run(self, stop_event=None, ts_queue=None):
        """ Start recording. """
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
                uvc_frame = self.capture.get_frame()

                # encode video frame
                if self.color_format == 'gray':
                    self.write(uvc_frame.gray)
                else:
                    self.write(uvc_frame.img)

                # save timestamp and fps
                timestamps.append(uvc_frame.timestamp)

                if uvc_frame.timestamp != self._last_timestamp:
                    fps = 1. / (uvc_frame.timestamp - self._last_timestamp)
                else:
                    fps = np.nan

                if ts_queue is not None:
                    ts_queue.put(fps)
                else:
                    self._fps_buffer.append(fps)

                self._last_timestamp = uvc_frame.timestamp

                # show video if requested
                if self.show_video:
                    # TODO set show_video to false when window is closed
                    self.show_frame(uvc_frame.img)

            except KeyboardInterrupt:
                break

        np.save(self.timestamp_file, np.array(timestamps))


class VideoRecorder(BaseRecorder):

    def __init__(self, folder, configs, quiet=False, show_video=False):
        """"""
        super(VideoRecorder, self).__init__(folder)
        self.captures = self._init_captures(self.folder, configs, show_video)
        self.quiet = quiet

        self._stdout_delay = 3.  # delay before showing fps on stdout
        self._max_queue_size = 20  # max size of process fps queue

    @classmethod
    def _init_captures(cls, folder, configs, show_video):
        """ Init VideoCapture instances for all configs. """
        return {
            c.device_name: VideoCapture(
                folder, c.device_name, c.resolution, c.fps, c.color_format,
                show_video=show_video)
            for c in configs
        }

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
        """ Start recording. """
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
