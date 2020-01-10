""""""
import os
import multiprocessing as mp
import time
from collections import namedtuple

import numpy as np

from pupil_recording_interface.recorder import BaseRecorder


VideoConfig = namedtuple(
    'VideoConfig', ['device_name', 'resolution', 'fps'])


class VideoEncoder(object):

    def __init__(self, folder, device_name, resolution, fps, codec='libx264',
                 overwrite=False):
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

        cmd = self._get_ffmpeg_cmd(
            self.video_file, resolution[::-1], fps, codec)
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        # timestamp writer
        self.timestamp_file = os.path.join(
            folder, '{}_timestamps.npy'.format(device_name))
        if os.path.exists(self.timestamp_file) and not overwrite:
            raise IOError(
                '{} exists, will not overwrite'.format(self.timestamp_file))

    @classmethod
    def _get_ffmpeg_cmd(
            cls, filename, frame_shape, fps, codec, format='bgr24'):
        """"""
        size = '{}x{}'.format(frame_shape[1], frame_shape[0])
        return ['ffmpeg', '-hide_banner', '-loglevel', 'panic', '-r', str(fps),
                '-an', '-f', 'rawvideo', '-s', size, '-pix_fmt', format,
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
    def _get_capture(cls, device_name, resolution, fps):
        """"""
        import uvc

        device_uids = {
            device['name']: device['uid'] for device in uvc.device_list()}

        try:
            capture = uvc.Capture(device_uids[device_name])
        except KeyError:
            raise ValueError(
                'Device with name {} not connected.'.format(device_name))

        capture.frame_mode = resolution + (fps,)

        return capture

    @classmethod
    def get_timestamp(cls):
        """"""
        import uvc
        return uvc.get_time_monotonic()

    def get_raw_frame(self, robust=False):
        """"""
        if robust:
            frame = self.capture.get_frame_robust()
        else:
            frame = self.capture.get_frame()

        return frame.img

    def show_frame(self, frame):
        """"""
        import cv2

        cv2.imshow(self.device_name, frame)
        return cv2.waitKey(1)


class VideoCapture(VideoEncoder, VideoDevice):

    def __init__(self, folder, device_name, resolution, fps, codec='libx264',
                 overwrite=False, show_video=False):
        """"""
        VideoDevice.__init__(self, device_name, resolution, fps,
                             init_capture=False)
        VideoEncoder.__init__(self, folder, device_name, resolution, fps,
                              codec, overwrite)

        self.show_video = show_video

    def _loop(self, event, lock):
        """"""
        with lock:
            # TODO uvc capture has to be initialized here for multi-threaded
            #  operation, check if we can circumvent this, e.g. with spawn()
            self.capture = self._get_capture(
                self.device_name, self.resolution, self.fps)

        timestamps = []

        while True:
            try:
                if event.is_set():
                    break
                frame = self.get_raw_frame()
                timestamps.append(self.get_timestamp())
                self.write(frame)
                if self.show_video:
                    self.show_frame(frame)

            except KeyboardInterrupt:
                break

        with lock:
            np.save(self.timestamp_file, np.array(timestamps))


class VideoRecorder(BaseRecorder):

    def __init__(self, folder, configs, quiet=False, show_video=False):
        """"""
        super(VideoRecorder, self).__init__(folder)
        self.captures = self._init_captures(self.folder, configs, show_video)
        self.quiet = quiet

    @classmethod
    def _init_captures(cls, folder, configs, show_video):
        """"""
        return {
            c.device_name: VideoCapture(folder, c.device_name, c.resolution,
                                        c.fps, show_video=show_video)
            for c in configs
        }

    @classmethod
    def _init_processes(cls, captures):
        """"""
        stop_event = mp.Event()
        processes = [mp.Process(target=c._loop, args=(stop_event, mp.Lock()))
                     for c in captures.values()]

        return processes, stop_event

    @classmethod
    def _start_processes(cls, processes):
        """"""
        for process in processes:
            process.start()

    @classmethod
    def _stop_processes(cls, processes, stop_event):
        """"""
        stop_event.set()
        for process in processes:
            process.join()

    def run(self):
        """"""
        if not self.quiet:
            print('Started recording to {}'.format(self.folder))

        processes, stop_event = self._init_processes(self.captures)
        self._start_processes(processes)

        while True:
            try:
                time.sleep(0.001)
            except KeyboardInterrupt:
                self._stop_processes(processes, stop_event)
                break

        if not self.quiet:
            print('Stopped recording')
