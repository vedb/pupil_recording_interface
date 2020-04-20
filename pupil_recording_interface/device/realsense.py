""""""
import multiprocessing as mp
import logging

import numpy as np

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device import BaseDevice


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

        queue_size: int, default 1
            Size of the video and odometry queues. If not None, frames will
            be dropped if the other ends of the queues cannot keep up with
            the device frame rates.
        """
        BaseDevice.__init__(self, device_uid)

        self.video = video
        self.odometry = odometry

        self.resolution = resolution
        self.fps = fps

        self.pipeline = None
        self.video_queue = mp.Queue(maxsize=queue_size) if self.video else None
        self.odometry_queue = (
            mp.Queue(maxsize=queue_size) if self.odometry else None
        )

    @classmethod
    def _from_config(cls, config, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(config, **kwargs)

        if config.stream_type == "video":
            # TODO this is a little hacky, maybe rename the parameter to "side"
            cls_kwargs["video"] = config.side
        elif config.stream_type == "odometry":
            cls_kwargs["odometry"] = True

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
            elif config.stream_type == "odometry":
                cls_kwargs["odometry"] = True
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
        if rs_frame.is_frameset() and self.video_queue is not None:
            if not self.video_queue.full():
                self.video_queue.put(
                    self._get_video_frame(rs_frame, self.video)
                )
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
            f"T265 pipeline started with video={video}, odometry={odometry}"
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
        return odometry, odometry["timestamp"]

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
                f"Stopping T265 pipeline for device: {self.device_uid}"
            )
            self.pipeline.stop()
            logger.debug(f"Pipeline stopped")
            self.pipeline = None
