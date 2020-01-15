""""""
import multiprocessing as mp

import numpy as np

import pyrealsense2 as rs

from pupil_recording_interface.device.video import BaseVideoDevice


class VideoDeviceT265(BaseVideoDevice):
    """ RealSense T265 video device. """

    def __init__(self, *args, **kwargs):
        """ Constructor. """
        self.frame_queue = mp.Queue()
        self.side = kwargs.pop('side', 'left')

        super(VideoDeviceT265, self).__init__(
            *args, callback=self._frame_callback, **kwargs)

    def _frame_callback(self, rs_frame):
        """ Callback for new RealSense frames. """
        if rs_frame.is_frameset():
            self.frame_queue.put(
                self._get_video_frame(rs_frame.as_frameset(), self.side))

    @classmethod
    def _get_video_frame(cls, frameset, side='left'):
        """ Extract video frame and timestamp from a frame set. """
        t = frameset.get_timestamp() / 1e3

        if side == 'left':
            video_frame = frameset.get_fisheye_frame(1).as_video_frame()
        elif side == 'right':
            video_frame = frameset.get_fisheye_frame(2).as_video_frame()
        elif side is True:
            # TODO return both frames
            video_frame = frameset.get_fisheye_frame(1).as_video_frame()
        else:
            raise ValueError('Unsupported mode: {}'.format(side))

        return np.asanyarray(video_frame.get_data()), t

    @classmethod
    def _get_capture(cls, device_name, resolution, fps, callback=None):
        """ Get a capture instance for a device by name. """
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.fisheye, 1)
        config.enable_stream(rs.stream.fisheye, 2)

        if callback is not None:
            pipeline.start(config, callback)
        else:
            pipeline.start(config)

        return pipeline

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        return self.frame_queue.get()

    def stop(self):
        """ Stop this device. """
        # self.capture is rs.pipeline
        # TODO self.capture.stop()
