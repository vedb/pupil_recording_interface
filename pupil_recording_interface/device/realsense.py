""""""
import numpy as np

import pyrealsense2 as rs

from pupil_recording_interface.device.video import BaseVideoDevice


class VideoDeviceT265(BaseVideoDevice):

    @classmethod
    def _get_capture(cls, device_name, resolution, fps):
        """ Get a capture instance for a device by name. """
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.fisheye, 1)
        config.enable_stream(rs.stream.fisheye, 2)

        pipeline.start(config)

        return pipeline

    @classmethod
    def _get_video_frame(cls, frameset, side='left'):
        """"""
        t = frameset.get_timestamp()

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

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        frameset = self.capture.wait_for_frames()
        return self._get_video_frame(frameset)
