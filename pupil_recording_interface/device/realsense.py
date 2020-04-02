""""""
import multiprocessing as mp
import logging

import numpy as np

from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import BaseVideoDevice
from pupil_recording_interface.config import VideoConfig, OdometryConfig


logger = logging.getLogger(__name__)


class RealSenseDeviceT265(BaseDevice):
    """ RealSense T265 device. """

    def __init__(
        self, uid, resolution=None, fps=None, video=False, odometry=False
    ):
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
        """
        BaseDevice.__init__(self, uid)

        self.video = video
        self.odometry = odometry

        self.resolution = resolution
        self.fps = fps

        self.pipeline = None
        self.video_queue = mp.Queue() if self.video else None
        self.odometry_queue = mp.Queue() if self.odometry else None

    @classmethod
    def from_config_list(cls, config_list, **extra_kwargs):
        """ Create a device from a list of configs. """
        # TODO make sure all configs have the same UID
        uid = config_list[0].device_uid

        try:
            from inspect import getfullargspec
        except ImportError:
            from inspect import getargspec as getfullargspec

        # get keyword arguments of this class
        argspect = getfullargspec(cls.__init__)
        kwargs = {
            k: v
            for k, v in zip(
                reversed(argspect.args), reversed(argspect.defaults)
            )
        }

        # set parameters for video and odometry devices
        for config in config_list:
            if isinstance(config, VideoConfig):
                kwargs["video"] = getattr(config, "side")
                kwargs.update(
                    {k: getattr(config, k) for k in ("resolution", "fps")}
                )
            elif isinstance(config, OdometryConfig):
                kwargs["odometry"] = True

        kwargs.update(extra_kwargs)

        logger.debug(
            "Creating T265 video device with serial number "
            "{uid} and parameters: {kwargs}".format(uid=uid, kwargs=kwargs)
        )

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
            "topic": "odometry",
            "timestamp": t,
            "tracker_confidence": c,
            "position": (p.x, p.y, p.z),
            "orientation": (q.w, q.x, q.y, q.z),
            "linear_velocity": (v.x, v.y, v.z),
            "angular_velocity": (w.x, w.y, w.z),
        }

    @classmethod
    def _get_video_frame(cls, rs_frame, side="both"):
        """ Extract video frame and timestamp from a RealSense frame. """
        frameset = rs_frame.as_frameset()
        t = frameset.get_timestamp() / 1e3

        if side == "left":
            video_frame = np.asanyarray(
                frameset.get_fisheye_frame(1).as_video_frame().get_data()
            )
        elif side == "right":
            video_frame = np.asanyarray(
                frameset.get_fisheye_frame(2).as_video_frame().get_data()
            )
        elif side == "both":
            video_frame = np.hstack(
                [
                    np.asanyarray(
                        frameset.get_fisheye_frame(1)
                        .as_video_frame()
                        .get_data()
                    ),
                    np.asanyarray(
                        frameset.get_fisheye_frame(2)
                        .as_video_frame()
                        .get_data()
                    ),
                ]
            )
        else:
            raise ValueError(f"Unsupported mode: {side}")

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

        logger.debug(
            "T265 pipeline started with video={video}, "
            "odometry={odometry}".format(video=video, odometry=odometry)
        )

        return pipeline

    def _get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        # TODO timestamp = uvc.get_time_monotonic()?
        return self.video_queue.get()

    def _get_odometry_and_timestamp(self):
        """ Get a frame and its associated timestamp. """
        odometry = self.odometry_queue.get()
        # TODO timestamp = uvc.get_time_monotonic()?
        return odometry, odometry["timestamp"]

    # TODO
    show_frame = BaseVideoDevice.show_frame

    def start(self):
        """ Start this device. """

    def stop(self):
        """ Stop this device. """

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching the recording thread. """
        if self.pipeline is None:
            self.pipeline = self._init_pipeline(
                self._frame_callback, self.video, self.odometry
            )

    def run_post_thread_hooks(self):
        """ Run hook(s) after the recording thread finishes. """
        if self.pipeline is not None:
            logger.debug(
                f"Stopping T265 pipeline for device: {self.uid}."
            )
            self.pipeline.stop()
            self.pipeline = None
