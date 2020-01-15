""""""
import multiprocessing as mp

import numpy as np

from pupil_recording_interface.device.video import BaseVideoDevice


class VideoDeviceT265(BaseVideoDevice):
    """ RealSense T265 video device. """

    def __init__(self, *args, **kwargs):
        """ Constructor. """
        self.side = kwargs.pop('side', 'left')
        self.odometry = kwargs.pop('odometry', True)

        self.video_queue = mp.Queue()
        self.odometry_queue = mp.Queue() if self.odometry else None

        super(VideoDeviceT265, self).__init__(
            *args, callback=self._frame_callback, odometry=self.odometry,
            **kwargs)

    def _frame_callback(self, rs_frame):
        """ Callback for new RealSense frames. """
        if rs_frame.is_frameset():
            self.video_queue.put(self._get_video_frame(rs_frame, self.side))
        elif rs_frame.is_pose_frame() and self.odometry_queue is not None:
            self.odometry_queue.put(self._get_odometry(rs_frame))

    @classmethod
    def _get_odometry(cls, rs_frame):
        """ Get odometry data from realsense pose frame. """
        t = rs_frame.get_timestamp() / 1e3

        pose = rs_frame.get_pose_frame()

        c = pose.pose_data.tracker_confidence
        p = pose.pose_data.translation
        q = pose.pose_data.rotation
        v = pose.pose_data.velocity
        w = pose.pose_data.angular_velocity

        return {
            'topic': 'odometry', 'timestamp': t, 'confidence': c,
            'position': (p.x, p.y, p.z),
            'orientation': (q.w, q.x, q.y, q.z),
            'linear_velocity': (v.x, v.y, v.z),
            'angular_velocity': (w.x, w.y, w.z)
        }

    @classmethod
    def _get_video_frame(cls, rs_frame, side='left'):
        """ Extract video frame and timestamp from a RealSense frame. """
        frameset = rs_frame.as_frameset()
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
    def _get_pipeline_config(cls, odometry=False):
        """ Get the pipeline config. """
        import pyrealsense2 as rs

        config = rs.config()
        config.enable_stream(rs.stream.fisheye, 1)
        config.enable_stream(rs.stream.fisheye, 2)

        if odometry:
            config.enable_stream(rs.stream.pose)

        return config

    @classmethod
    def _get_capture(cls, device_name, resolution, fps, callback=None,
                     odometry=False):
        """ Get a capture instance for a device by name. """
        import pyrealsense2 as rs

        pipeline = rs.pipeline()
        config = cls._get_pipeline_config()

        if callback is not None:
            pipeline.start(config, callback)
        else:
            pipeline.start(config)

        return pipeline

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        return self.video_queue.get()

    def stop(self):
        """ Stop this device. """
        # self.capture is rs.pipeline
        # TODO self.capture.stop(), looks like this doesn't work if the
        #  pipeline wasn't started in the same thread as the one where this
        #  method is called.
