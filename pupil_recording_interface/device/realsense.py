""""""
from inspect import getfullargspec
import multiprocessing as mp

import numpy as np

from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import BaseVideoDevice
from pupil_recording_interface.config import VideoConfig, OdometryConfig


class RealSenseDeviceT265(BaseDevice):
    """ RealSense T265 device. """

    def __init__(self, uid, resolution=None, fps=None,
                 video=False, odometry=False, start=True):
        """ Constructor.

        Parameters
        ----------
        uid: str
            The unique identity of this device. Depending on the device this
            will be a serial number or similar.

        resolution: tuple, len 2, optional
            Desired horizontal and vertical camera resolution.

        fps: int, optional
            Desired camera refresh rate.

        video: str, optional
            If specified, which fisheye camera to stream. Can be 'left',
            'right', or 'both'.

        odometry: bool, default False
            If True, activate the odometry stream.

        start: bool, default True
            If True, initialize the underlying capture upon construction.
            Set to False for multi-threaded recording.
        """
        BaseDevice.__init__(self, uid)

        self.video = video
        self.odometry = odometry

        self.resolution = resolution
        self.fps = fps

        self.video_queue = mp.Queue() if self.video else None
        self.odometry_queue = mp.Queue() if self.odometry else None

        if start:
            self.pipeline = self._init_pipeline(
                self._frame_callback, self.video, self.odometry)
        else:
            self.pipeline = None

    @classmethod
    def from_config_list(cls, config_list, **extra_kwargs):
        """ Create a device from a list of configs. """
        # TODO make sure all configs have the
        uid = config_list[0].device_uid

        argspect = getfullargspec(cls.__init__)
        kwargs = {k: v for k, v in
                  zip(reversed(argspect.args), reversed(argspect.defaults))}
        for config in config_list:
            if isinstance(config, VideoConfig):
                kwargs['video'] = 'both'  # TODO make configurable
                kwargs.update(
                    {k: getattr(config, k) for k in ('resolution', 'fps')})
            elif isinstance(config, OdometryConfig):
                kwargs['odometry'] = True

        kwargs.update(extra_kwargs)

        return cls(uid, **kwargs)

    @property
    def is_started(self):
        return self.pipeline is not None

    def _frame_callback(self, rs_frame):
        """ Callback for new RealSense frames. """
        if rs_frame.is_frameset() and self.video_queue is not None:
            self.video_queue.put(self._get_video_frame(rs_frame, self.video))
        elif rs_frame.is_pose_frame() and self.odometry_queue is not None:
            self.odometry_queue.put(self._get_odometry(rs_frame))

    @classmethod
    def _get_odometry(cls, rs_frame):
        """ Get odometry data from realsense pose frame. """
        pose = rs_frame.as_pose_frame()
        t = rs_frame.get_timestamp() / 1e3

        c = pose.pose_data.tracker_confidence
        p = pose.pose_data.translation
        q = pose.pose_data.rotation
        v = pose.pose_data.velocity
        w = pose.pose_data.angular_velocity

        return {
            'topic': 'odometry',
            'timestamp': t,
            'tracker_confidence': c,
            'position': (p.x, p.y, p.z),
            'orientation': (q.w, q.x, q.y, q.z),
            'linear_velocity': (v.x, v.y, v.z),
            'angular_velocity': (w.x, w.y, w.z)
        }

    @classmethod
    def _get_video_frame(cls, rs_frame, side='both'):
        """ Extract video frame and timestamp from a RealSense frame. """
        frameset = rs_frame.as_frameset()
        t = frameset.get_timestamp() / 1e3

        if side == 'left':
            video_frame = np.asanyarray(
                frameset.get_fisheye_frame(1).as_video_frame().get_data())
        elif side == 'right':
            video_frame = np.asanyarray(
                frameset.get_fisheye_frame(2).as_video_frame().get_data())
        elif side == 'both':
            video_frame = np.hstack([
                np.asanyarray(
                    frameset.get_fisheye_frame(1).as_video_frame().get_data()),
                np.asanyarray(
                    frameset.get_fisheye_frame(2).as_video_frame().get_data())
            ])
        else:
            raise ValueError('Unsupported mode: {}'.format(side))

        return video_frame, t

    @classmethod
    def _get_pipeline_config(cls, video=False, odometry=False):
        """ Get the pipeline config. """
        import pyrealsense2 as rs

        config = rs.config()

        if video:
            config.enable_stream(rs.stream.fisheye, 1)
            config.enable_stream(rs.stream.fisheye, 2)

        if odometry:
            config.enable_stream(rs.stream.pose)

        return config

    @classmethod
    def _init_pipeline(cls, callback, video=False, odometry=False):
        """ Init the pipeline. """
        import pyrealsense2 as rs

        pipeline = rs.pipeline()
        config = cls._get_pipeline_config(video, odometry)

        if callback is not None:
            pipeline.start(config, callback)
        else:
            pipeline.start(config)

        return pipeline

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        # TODO timestamp = uvc.get_time_monotonic()?
        return self.video_queue.get()

    def _get_odometry_and_timestamp(self):
        """ Get a frame and its associated timestamp. """
        odometry = self.odometry_queue.get()
        # TODO timestamp = uvc.get_time_monotonic()?
        return odometry, odometry['timestamp']

    show_frame = BaseVideoDevice.show_frame

    def stop(self):
        """ Stop this device. """
        # TODO self.pipeline.stop(), looks like this doesn't work if the
        #  pipeline wasn't started in the same thread as the one where this
        #  method is called.
        if self.pipeline is not None:
            self.pipeline.stop()
            self.pipeline = None


class VideoDeviceT265(RealSenseDeviceT265, BaseVideoDevice):
    """ RealSense T265 video device. """

    def __init__(self, *args, **kwargs):
        kwargs['video'] = kwargs.get('video', 'both')
        # TODO check if this can lead to unexpected behavior
        kwargs['odometry'] = False
        super(VideoDeviceT265, self).__init__(*args, **kwargs)
        self.capture_kwargs = {'callback': self._frame_callback}

    @classmethod
    def _get_capture(cls, uid, resolution, fps, callback=None):
        """ Get a capture instance for a device by name. """
        # TODO this should not need to be called because the pipeline has to
        #  be started in the main thread
        return cls._init_pipeline(callback, video=True, odometry=False)

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        # TODO timestamp = uvc.get_time_monotonic()?
        return self.video_queue.get()


class OdometryDeviceT265(RealSenseDeviceT265):
    """ RealSense T265 odometry device. """

    def __init__(self, *args, **kwargs):
        kwargs['odometry'] = True
        # TODO check if this can lead to unexpected behavior
        kwargs['video'] = False
        super(OdometryDeviceT265, self).__init__(*args, **kwargs)

    def _get_odometry_and_timestamp(self):
        """ Get a frame and its associated timestamp. """
        odometry = self.odometry_queue.get()
        # TODO timestamp = uvc.get_time_monotonic()?
        return odometry, odometry['timestamp']
