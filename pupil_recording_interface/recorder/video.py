import os

import numpy as np

from pupil_recording_interface.recorder import BaseRecorder


class VideoDevice(object):

    def __init__(self, device_name, resolution, fps):
        """"""
        self.device_name = device_name
        self.resolution = resolution
        self.fps = fps
        self.capture = self._get_capture(device_name, resolution, fps)

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

    def get_raw_frame(self):
        """"""
        frame = self.capture.get_frame_robust()
        return frame.img

    def show_frame(self, frame):
        """"""
        import cv2

        cv2.imshow(self.device_name, frame)
        return cv2.waitKey(1)


class VideoRecoder(BaseRecorder, VideoDevice):

    def __init__(self, folder, device_name, resolution, fps, codec='libx264',
                 overwrite=False, quiet=False, show_video=False):
        """"""
        import subprocess

        BaseRecorder.__init__(self, folder)
        VideoDevice.__init__(self, device_name, resolution, fps)

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

        self.quiet = quiet
        self.show_video = show_video

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

    def run(self):
        """"""
        if not self.quiet:
            print('Started recording to {}'.format(self.folder))

        timestamps = []

        while True:
            try:
                frame = self.get_raw_frame()
                timestamps.append(self.get_timestamp())
                self.write(frame)
                if self.show_video:
                    self.show_frame(frame)
            except KeyboardInterrupt:
                break

        np.save(self.timestamp_file, np.array(timestamps))

        if not self.quiet:
            print('Stopped recording')