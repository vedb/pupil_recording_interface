""""""
import multiprocessing as mp
import logging

import numpy as np

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.utils import monotonic


logger = logging.getLogger(__name__)


@device("t265")
class RealSenseDeviceT265(BaseDevice):
    """ RealSense T265 device. """

    def __init__(
        self,
        device_uid,
        resolution=None,
        fps=None,
        video=False,
        odometry=False,
        accel=False,
        gyro=False,
        queue_size=1,
    ):
        """ Constructor.

        Parameters
        ----------
        device_uid: str
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

        accel: bool, default False
            If True, activate the accelerometer stream.

        gyro: bool, default False
            If True, activate the gyroscope stream.

        queue_size: int, default 1
            Size of the video and odometry queues. If not None, frames will
            be dropped if the other ends of the queues cannot keep up with
            the device frame rates.
        """
        BaseDevice.__init__(self, device_uid)

        self.resolution = resolution
        self.fps = fps
        self.video = video
        self.odometry = odometry
        self.accel = accel
        self.gyro = gyro

        self.timebase = "epoch"

        self.pipeline = None
        self.video_queue = mp.Queue(maxsize=queue_size) if self.video else None
        self.odometry_queue = (
            mp.Queue(maxsize=queue_size) if self.odometry else None
        )
        self.accel_queue = mp.Queue(maxsize=queue_size) if self.accel else None
        self.gyro_queue = mp.Queue(maxsize=queue_size) if self.gyro else None

    @classmethod
    def _from_config(cls, config, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(config, **kwargs)

        if config.stream_type == "video":
            # TODO this is a little hacky, maybe rename the parameter to "side"
            cls_kwargs["video"] = config.side
        elif config.stream_type == "odometry":
            cls_kwargs["odometry"] = True
        elif config.stream_type == "accel":
            cls_kwargs["accel"] = True
        elif config.stream_type == "gyro":
            cls_kwargs["gyro"] = True

        return cls(**cls_kwargs)

    @classmethod
    def from_config_list(cls, config_list, **kwargs):
        """ Create a device from a list of configs. """
        # TODO make sure all configs have the same UID
        uid = config_list[0].device_uid

        _, cls_kwargs = cls.get_params()

        # set parameters for video and odometry devices
        for config in config_list:
            if config.stream_type == "video":
                cls_kwargs["video"] = config.side
                cls_kwargs.update(
                    {k: getattr(config, k) for k in ("resolution", "fps")}
                )
            elif config.stream_type == "motion":
                if config.motion_type == "odometry":
                    cls_kwargs["odometry"] = True
                elif config.motion_type == "accel":
                    cls_kwargs["accel"] = True
                elif config.motion_type == "gyro":
                    cls_kwargs["gyro"] = True
                else:
                    raise ValueError(
                        f"Unsupported motion type: {config.motion_type}"
                    )
            else:
                raise ValueError(
                    f"Unsupported stream type: {config.stream_type}"
                )

        cls_kwargs.update(kwargs)

        logger.debug(
            f"Creating T265 video device with serial number {uid} "
            f"and parameters: {cls_kwargs}"
        )

        return cls(uid, **cls_kwargs)

    @property
    def is_started(self):
        return self.pipeline is not None

    def _frame_callback(self, rs_frame):
        """ Callback for new RealSense frames. """
        import pyrealsense2 as rs

        if rs_frame.is_frameset() and self.video_queue is not None:
            if not self.video_queue.full():
                self.video_queue.put(
                    self._get_video_frame(rs_frame, self.video)
                )
        elif rs_frame.is_pose_frame() and self.odometry_queue is not None:
            self.odometry_queue.put(self._get_odometry(rs_frame))
        elif (
            rs_frame.is_motion_frame()
            and rs_frame.profile.stream_type() == rs.stream.accel
            and self.accel_queue is not None
        ):
            self.accel_queue.put(self._get_accel(rs_frame))
        elif (
            rs_frame.is_motion_frame()
            and rs_frame.profile.stream_type() == rs.stream.gyro
            and self.gyro_queue is not None
        ):
            self.gyro_queue.put(self._get_gyro(rs_frame))

    @classmethod
    def _get_odometry(cls, rs_frame):
        """ Get odometry data from realsense pose frame. """
        t = monotonic()

        pose = rs_frame.as_pose_frame()
        t_src = rs_frame.get_timestamp() / 1e3
        c = pose.pose_data.tracker_confidence
        p = pose.pose_data.translation
        q = pose.pose_data.rotation
        v = pose.pose_data.velocity
        w = pose.pose_data.angular_velocity

        return {
            "topic": "odometry",
            "timestamp": t,
            "source_timestamp": t_src,
            "tracker_confidence": c,
            "position": (p.x, p.y, p.z),
            "orientation": (q.w, q.x, q.y, q.z),
            "linear_velocity": (v.x, v.y, v.z),
            "angular_velocity": (w.x, w.y, w.z),
        }

    @classmethod
    def _get_accel(cls, rs_frame):
        """ Get accelerometer data from realsense motion frame. """
        t = monotonic()

        motion = rs_frame.as_motion_frame()
        t_src = rs_frame.get_timestamp() / 1e3
        a = motion.motion_data

        return {
            "topic": "accel",
            "timestamp": t,
            "source_timestamp": t_src,
            "linear_acceleration": (a.x, a.y, a.z),
        }

    @classmethod
    def _get_gyro(cls, rs_frame):
        """ Get gyroscope data from realsense motion frame. """
        t = monotonic()

        motion = rs_frame.as_motion_frame()
        t_src = rs_frame.get_timestamp() / 1e3
        w = motion.motion_data

        return {
            "topic": "gyro",
            "timestamp": t,
            "source_timestamp": t_src,
            "angular_velocity": (w.x, w.y, w.z),
        }

    @classmethod
    def _get_video_frame(cls, rs_frame, side="both"):
        """ Extract video frame and timestamp from a RealSense frame. """
        t = monotonic()

        frameset = rs_frame.as_frameset()
        t_src = frameset.get_timestamp() / 1e3

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

        return video_frame, t, t_src

    @classmethod
    def _get_pipeline_config(
        cls, video=False, odometry=False, accel=False, gyro=False
    ):
        """ Get the pipeline config. """
        import pyrealsense2 as rs

        config = rs.config()

        if video:
            config.enable_stream(rs.stream.fisheye, 1)
            config.enable_stream(rs.stream.fisheye, 2)

        if odometry:
            config.enable_stream(rs.stream.pose)

        if accel:
            config.enable_stream(rs.stream.accel)

        if gyro:
            config.enable_stream(rs.stream.gyro)

        return config

    @classmethod
    def _init_pipeline(
        cls, callback, video=False, odometry=False, accel=False, gyro=False
    ):
        """ Init the pipeline. """
        import pyrealsense2 as rs

        pipeline = rs.pipeline()
        config = cls._get_pipeline_config(video, odometry, accel, gyro)

        if callback is not None:
            pipeline.start(config, callback)
        else:
            pipeline.start(config)

        logger.debug(
            f"T265 pipeline started with video={video}, odometry={odometry},"
            f"accel={accel}, gyro={gyro}"
        )

        return pipeline

    def _get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        # TODO timestamp = uvc.get_time_monotonic()?
        # TODO timeout
        return self.video_queue.get()

    def _get_odometry_and_timestamp(self):
        """ Get a frame and its associated timestamp. """
        odometry = self.odometry_queue.get()
        # TODO timestamp = uvc.get_time_monotonic()?
        # TODO timeout
        return odometry, odometry["timestamp"], odometry["source_timestamp"]

    def _get_accel_and_timestamp(self):
        """ Get a frame and its associated timestamp. """
        accel = self.accel_queue.get()
        # TODO timestamp = uvc.get_time_monotonic()?
        # TODO timeout
        return accel, accel["timestamp"], accel["source_timestamp"]

    def _get_gyro_and_timestamp(self):
        """ Get a frame and its associated timestamp. """
        gyro = self.gyro_queue.get()
        # TODO timestamp = uvc.get_time_monotonic()?
        # TODO timeout
        return gyro, gyro["timestamp"], gyro["source_timestamp"]

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching the recording thread. """
        if self.pipeline is None:
            self.pipeline = self._init_pipeline(
                self._frame_callback,
                self.video,
                self.odometry,
                self.accel,
                self.gyro,
            )

    def run_post_thread_hooks(self):
        """ Run hook(s) after the recording thread finishes. """
        if self.pipeline is not None:
            logger.debug(
                f"Stopping T265 pipeline for device: {self.device_uid}"
            )
            self.pipeline.stop()
            logger.debug(f"Pipeline stopped")
            self.pipeline = None
