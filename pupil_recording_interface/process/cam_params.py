""""""
from itertools import combinations
from queue import Queue, Full
from threading import Lock
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.methods import gen_pattern_grid
from pupil_recording_interface.externals.file_methods import (
    save_intrinsics,
    save_extrinsics,
)

logger = logging.getLogger(__name__)


@process("circle_grid_detector")
class CircleGridDetector(BaseProcess):
    """ Detector for circle grids. """

    def __init__(
        self, grid_shape=(4, 11), stereo=False, display=True, **kwargs,
    ):
        """ Constructor. """
        self.grid_shape = grid_shape
        self.stereo = stereo
        self.display = display

        super().__init__(**kwargs)

    def detect_grid(self, packet):
        """ Detect circle grid in frame. """
        frame = packet["frame"]

        if packet.color_format == "bggr8":
            frame = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2GRAY)

        if self.stereo:
            status_left, grid_points_left = cv2.findCirclesGrid(
                frame[:, : frame.shape[1] // 2],
                self.grid_shape,
                flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )
            status_right, grid_points_right = cv2.findCirclesGrid(
                frame[:, frame.shape[1] // 2 :],
                self.grid_shape,
                flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )
            if status_right:
                grid_points_right[:, :, 0] += frame.shape[1] // 2

            status = status_left and status_right
            grid_points = [grid_points_left, grid_points_right]
        else:
            status, grid_points = cv2.findCirclesGrid(
                frame, self.grid_shape, flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )

        if status:
            return {
                "grid_points": grid_points,
                "resolution": frame.shape[1::-1],
                "stereo": self.stereo,
            }
        else:
            return None

    def display_hook(self, packet):
        """ Add circle grid overlay onto frame. """
        circle_grid = packet["circle_grid"]
        if circle_grid is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame
        else:
            grid_points = circle_grid["grid_points"]

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        if isinstance(grid_points, list):
            calib_bounds = [
                cv2.convexHull(gp).astype(np.int32) for gp in grid_points
            ]
        else:
            calib_bounds = [cv2.convexHull(grid_points).astype(np.int32)]

        # TODO make constructor arguments
        color = (0, 255, 0)

        cv2.polylines(frame, calib_bounds, True, color)

        return frame

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.circle_grid = self.call(self.detect_grid, packet, block=block)

        # TODO maybe don't broadcast on every single packet
        packet.broadcasts.append("circle_grid")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet


def calculate_intrinsics(
    resolution, img_points, obj_points, dist_mode="radial"
):
    """ Calculate intrinsic parameters for one camera. """
    logger.debug(f"Calibrating camera with resolution: {resolution}")

    obj_points = [obj_points.reshape(1, -1, 3) for _ in range(len(img_points))]

    if dist_mode.lower() == "fisheye":
        calibration_flags = (
            cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
            + cv2.fisheye.CALIB_FIX_SKEW
            + cv2.fisheye.CALIB_CHECK_COND
        )

        max_iter = 30
        eps = 1e-6

        camera_matrix = np.eye(3, dtype=np.float64)
        dist_coefs = np.zeros((4, 1), dtype=np.float64)
        rms, _, _, _, _ = cv2.fisheye.calibrate(
            obj_points,
            img_points,
            resolution[::-1],
            camera_matrix,
            dist_coefs,
            flags=calibration_flags,
            criteria=(
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                max_iter,
                eps,
            ),
        )
        logger.debug(f"Calibrated camera, RMS:{rms:.6f}")
        return camera_matrix, dist_coefs

    elif dist_mode.lower() == "radial":
        rms, camera_matrix, dist_coefs, _, _ = cv2.calibrateCamera(
            obj_points, img_points, resolution[::-1], None, None,
        )
        logger.debug(f"Calibrated camera, RMS:{rms:.6f}")
        return camera_matrix, dist_coefs

    else:
        logger.error(f"Unknown distortion model: {dist_mode}")
        return None, None


def calculate_extrinsics(
    img_points_a,
    img_points_b,
    obj_points,
    cam_mtx_a,
    dist_coefs_a,
    cam_mtx_b,
    dist_coefs_b,
    dist_mode="radial",
):
    """ Calculate extrinsics for pairs of cameras. """
    logger.debug("Calculating extrinsics for camera pair")

    img_points_a = [x.reshape(1, -1, 2) for x in img_points_a]
    img_points_b = [x.reshape(1, -1, 2) for x in img_points_b]
    obj_points = [
        obj_points.reshape(1, -1, 3) for _ in range(len(img_points_a))
    ]

    if dist_mode.lower() == "fisheye":
        rms, _, _, _, _, R, T = cv2.fisheye.stereoCalibrate(
            obj_points,
            img_points_a,
            img_points_b,
            cam_mtx_a,
            dist_coefs_a,
            cam_mtx_b,
            dist_coefs_b,
            (0, 0),
            flags=cv2.CALIB_FIX_INTRINSIC,
        )
        return R, T

    elif dist_mode.lower() == "radial":
        rms, _, _, _, _, R, T, _, _ = cv2.stereoCalibrate(
            obj_points,
            img_points_a,
            img_points_b,
            cam_mtx_a,
            dist_coefs_a,
            cam_mtx_b,
            dist_coefs_b,
            (0, 0),
            flags=cv2.CALIB_FIX_INTRINSIC,
        )
        return R, T

    else:
        logger.error(f"Unknown distortion model: {dist_mode}")
        return None, None


@process("cam_param_estimator", optional=("folder",))
class CamParamEstimator(BaseProcess):
    """ Camera parameter estimator. """

    def __init__(
        self,
        streams,
        folder,
        grid_shape=(4, 11),
        num_patterns=10,
        distortion_model="radial",
        extrinsics=False,
        display=True,
        **kwargs,
    ):
        """ Constructor. """
        self.streams = streams
        self.folder = folder
        self.num_patterns = num_patterns
        self.distortion_model = distortion_model
        self.extrinsics = extrinsics
        self.display = display

        if len(streams) > 1 and not extrinsics:
            logger.warning(
                "Estimating intrinsics for multiple cameras simultaneously "
                "will likely yield poorer results than individual estimates."
            )

        super().__init__(listen_for=["circle_grid"], **kwargs)

        self.intrinsics = None
        self.extrinsics = None

        self._obj_points = gen_pattern_grid(grid_shape)
        self._pattern_queue = Queue(maxsize=self.num_patterns)
        self._acquire_pattern = False
        self._pattern_acquired = False
        self._lock = Lock()

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls.get_constructor_args(
            config, folder=config.folder or kwargs.get("folder", None),
        )

        return cls(**cls_kwargs)

    def _add_pattern(self, circle_grid):
        """ Add a new pattern to the queue. """
        self._pattern_queue.put(circle_grid, False)
        logger.info(
            f"Captured pattern {self._pattern_queue.qsize()} of "
            f"{self.num_patterns}"
        )

        if self._pattern_queue.full():
            self._estimate_params()

    @classmethod
    def _add_grid_points(
        cls, patterns, resolutions, camera, grid_points, resolution
    ):
        """ Add grid points to the pattern dict. """
        if camera not in resolutions:
            resolutions[camera] = resolution
        elif resolution != resolutions[camera]:
            raise ValueError(f"Got multiple resolutions for camera: {camera}")
        if camera not in patterns:
            patterns[camera] = []
        patterns[camera].append(grid_points)

    def _get_patterns(self):
        """ Get patterns from pattern queue by camera. """
        resolutions, patterns = {}, {}

        while not self._pattern_queue.empty():
            pattern = self._pattern_queue.get()
            for device, circle_grid in pattern.items():
                if circle_grid["stereo"]:
                    resolution = (
                        circle_grid["resolution"][0] // 2,
                        circle_grid["resolution"][1],
                    )
                    # TODO the Packet class should not be passing around
                    #  mutable attributes...
                    grid_points_right = circle_grid["grid_points"][1].copy()
                    grid_points_right[:, :, 0] -= resolution[0]
                    self._add_grid_points(
                        patterns,
                        resolutions,
                        device + "_left",
                        circle_grid["grid_points"][0],
                        resolution,
                    )
                    self._add_grid_points(
                        patterns,
                        resolutions,
                        device + "_right",
                        grid_points_right,
                        resolution,
                    )
                else:
                    self._add_grid_points(
                        patterns,
                        resolutions,
                        device,
                        circle_grid["grid_points"],
                        circle_grid["resolution"],
                    )

        return resolutions, patterns

    @classmethod
    def _save_intrinsics(cls, folder, intrinsics):
        """ Save estimated intrinsics. """
        for (
            device,
            (resolution, dist_mode, cam_mtx, dist_coefs),
        ) in intrinsics.items():
            save_intrinsics(
                folder,
                device,
                resolution,
                {
                    "camera_matrix": cam_mtx.tolist(),
                    "dist_coefs": dist_coefs.tolist(),
                    "cam_type": dist_mode,
                    "resolution": list(resolution),
                },
            )

    @classmethod
    def _save_extrinsics(cls, folder, extrinsics):
        """ Save estimated intrinsics. """
        for ((first, second), (resolution, R, T)) in extrinsics.items():
            save_extrinsics(
                folder,
                first,
                resolution,
                {
                    second: {
                        "order": "first",
                        "rotation": R,
                        "translation": T,
                        "resolution": list(resolution),
                    }
                },
            )
            save_extrinsics(
                folder,
                second,
                resolution,
                {
                    first: {
                        "order": "second",
                        "rotation": R,
                        "translation": T,
                        "resolution": list(resolution),
                    }
                },
            )

    def _estimate_params(self):
        """ Estimate camera parameters. """
        logger.debug("Estimating camera parameters")

        resolutions, patterns = self._get_patterns()

        try:
            self.intrinsics = {
                camera: (
                    resolutions[camera],
                    self.distortion_model,
                    *calculate_intrinsics(
                        resolutions[camera], patterns[camera], self._obj_points
                    ),
                )
                for camera in patterns
            }
        except cv2.error as e:
            logger.warning(
                f"Intrinsics estimation failed. Reason: {e}\n"
                f"Please try again with a better coverage of the camera's FOV!"
            )
            return

        # Skip saving intrinsics when estimating extrinsics because the
        # calibration data will most likely be poorer than when estimating
        # intrinsics for each stream individually
        if not self.extrinsics:
            self._save_intrinsics(self.folder, self.intrinsics)

        if self.extrinsics:
            try:
                self.extrinsics = {
                    (camera_1, camera_2): (
                        resolutions[camera_1],
                        resolutions[camera_2],
                        *calculate_extrinsics(
                            patterns[camera_1],
                            patterns[camera_2],
                            self._obj_points,
                            self.intrinsics[camera_1][0],
                            self.intrinsics[camera_1][1],
                            self.intrinsics[camera_2][0],
                            self.intrinsics[camera_2][1],
                        ),
                    )
                    for camera_1, camera_2 in combinations(patterns, 2)
                }
            except cv2.error as e:
                logger.warning(f"Extrinsics estimation failed. Reason: {e}")
                return

            self._save_extrinsics(self.folder, self.extrinsics)

        logger.info("Successfully estimated camera parameters")

    def display_hook(self, packet):
        """ Add circle grid overlay onto frame. """
        if self.context is None:
            # TODO check if it makes sense to show the grid without a context
            return packet.display_frame

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        for pattern_dict in list(self._pattern_queue.queue):
            grid_points = pattern_dict[self.context.device.device_uid][
                "grid_points"
            ]
            if isinstance(grid_points, list):
                calib_bounds = [
                    cv2.convexHull(gp).astype(np.int32) for gp in grid_points
                ]
            else:
                calib_bounds = [cv2.convexHull(grid_points).astype(np.int32)]

            # TODO make constructor arguments
            color = (200, 100, 0)

            cv2.polylines(frame, calib_bounds, True, color)

        return frame

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            # check for triggers
            if (
                "acquire_pattern" in notification
                and notification["acquire_pattern"]
            ):
                self._acquire_pattern = True

            # collect new data
            if self._acquire_pattern:
                # TODO with self._lock?
                try:
                    # Add data from notifications
                    pattern_dict = {
                        notification[stream]["device_uid"]: notification[
                            stream
                        ]["circle_grid"]
                        for stream in self.streams
                    }
                    # Check if we got grid points from all streams
                    if any(
                        pattern is None for pattern in pattern_dict.values()
                    ):
                        continue
                    else:
                        self._acquire_pattern = False
                    self._add_pattern(pattern_dict)
                    self._pattern_acquired = True
                except KeyError:
                    pass
                except Full:
                    break

    def _process_packet(self, packet, block=None):
        """ Process a packet. """
        if self._pattern_acquired:
            packet.pattern_acquired = True
            self._pattern_acquired = False
        else:
            packet.pattern_acquired = False

        packet.broadcasts.append("pattern_acquired")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet
