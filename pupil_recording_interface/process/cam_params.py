""""""
from itertools import combinations
from queue import Queue, Full
from threading import Lock
from typing import Optional, Iterable
import logging
import os

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
    """ Detector for circle grids.

    This process detects the asymmetrical circle grid for camera parameter
    estimation (intrinsic and extrinsic). Attach one to each stream for which
    you want to estimate camera parameters.
    """

    def __init__(
        self,
        grid_shape: tuple = (4, 11),
        scale: Optional[float] = None,
        stereo: bool = False,
        display: bool = True,
        **kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        grid_shape:
            Number of rows and columns of the grid.

        scale:
            If specified, resize the camera frame by this scale factor before
            detection. This will increase the speed of detection at the
            expense of accuracy.

        stereo:
            If True, the camera frames are assumed to be stereo images and
            grids will be detected both in the left and the right half.

        display:
            If True, add this instance's ``display_hook`` method to the packet
            returned by ``process_packet``. A ``VideoDisplay`` later in the
            pipeline will pick this up to draw the extent of the currently
            detected grid over the camera image.
        """
        self.grid_shape = grid_shape
        self.scale = scale
        self.stereo = stereo
        self.display = display

        super().__init__(**kwargs)

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

    def _process_packet(self, packet):
        """ Process a new packet. """
        packet.circle_grid = self.detect_grid(
            packet.frame, packet.color_format
        )

        # TODO maybe don't broadcast on every single packet
        packet.broadcasts.append("circle_grid")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet

    def detect_grid(self, frame, color_format):
        """ Detect circle grid in frame. """
        if color_format == "bggr8":
            frame = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2GRAY)

        resolution = frame.shape[1::-1]
        if self.scale is not None:
            frame = cv2.resize(
                frame,
                None,
                fx=self.scale,
                fy=self.scale,
                interpolation=cv2.INTER_AREA,
            )

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
            if status_left and self.scale is not None:
                grid_points_left /= self.scale
            if status_right:
                if self.scale is not None:
                    grid_points_right /= self.scale
                grid_points_right[:, :, 0] += resolution[0] // 2

            status = status_left and status_right
            grid_points = [grid_points_left, grid_points_right]
        else:
            status, grid_points = cv2.findCirclesGrid(
                frame, self.grid_shape, flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )
            if status and self.scale is not None:
                grid_points /= self.scale

        if status:
            return {
                "grid_points": grid_points,
                "resolution": resolution,
                "stereo": self.stereo,
            }
        else:
            return None


def calculate_intrinsics(
    resolution, img_points, obj_points, dist_mode="radial"
):
    """ Calculate intrinsic parameters for one camera. """
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
    """ Camera parameter estimator.

    This process estimates camera parameters (intrinsic and extrinsic) for one
    or multiple cameras based on the locations of calibration patterns detected
    e.g. by the CircleGridDetector. You only need to attach one to one of the
    video streams, even when estimating extrinsics between multiple cameras.
    """

    def __init__(
        self,
        streams: Iterable[str],
        folder: os.PathLike,
        grid_shape: tuple = (4, 11),
        grid_scale: float = 0.02,
        num_patterns: int = 10,
        distortion_model: str = "radial",
        extrinsics: bool = False,
        display: bool = True,
        **kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        streams:
            Names of video streams for which to perform estimation.

        folder:
            Folder for saving estimation results.

        grid_shape:
            Number of rows and columns of the grid.

        grid_scale:
            Distance between grid positions in meters. Can be calculated by
            measuring the distance between the centers of the outermost circles
            in the first row (the longer on) on the printed calibration target.
            Divide this distance by the number of horizontal grid positions
            (default 11) to obtain the scale.

        num_patterns:
            Number of patterns to capture before performing estimation.

        distortion_model:
            Distortion model to use for estimation. Can be "radial" or
            "fisheye".

        extrinsics:
            If True, perform extrinsics estimation (rotation and translation)
            between cameras. Requires at least two streams or one fisheye
            stream. This will not save the intrinsics because the calibration
            data will most likely be poorer than when estimatingintrinsics for
            each stream individually.

        display:
            If True, add this instance's ``display_hook`` method to the packet
            returned by ``process_packet``. A ``VideoDisplay`` later in the
            pipeline will pick this up to draw the extent of the all previously
            detected grids over the camera image.
        """
        self.streams = streams
        self.folder = folder
        self.num_patterns = num_patterns
        self.distortion_model = distortion_model
        self.estimate_extrinsics = extrinsics
        self.display = display

        if len(streams) > 1 and not extrinsics:
            logger.warning(
                "Estimating intrinsics for multiple cameras simultaneously "
                "will likely yield poorer results than individual estimates."
            )

        super().__init__(listen_for=["circle_grid"], **kwargs)

        self._intrinsics_result = None
        self._extrinsics_result = None

        self._obj_points = gen_pattern_grid(grid_shape) * grid_scale
        self._pattern_queue = Queue(maxsize=self.num_patterns)
        self._acquire_pattern = False
        self._pattern_acquired = False
        self._lock = Lock()

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls._get_constructor_args(
            config, folder=config.folder or kwargs.get("folder", None),
        )

        return cls(**cls_kwargs)

    def display_hook(self, packet):
        """ Add circle grid overlay onto frame. """
        if self.context is None:
            # TODO check if it makes sense to show the grid without a context
            return packet.display_frame

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        for pattern_dict in list(self._pattern_queue.queue):
            try:
                grid_points = pattern_dict[self.context.device.device_uid][
                    "grid_points"
                ]
            except KeyError:
                continue

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

    def _process_notifications(self, notifications):
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

    def _process_packet(self, packet):
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
        for (cam_1, cam_2), (res_1, res_2, R, T) in extrinsics.items():
            save_extrinsics(
                folder,
                cam_1,
                res_1,
                {
                    cam_2: {
                        "order": "first",
                        "rotation": R.tolist(),
                        "translation": T.tolist(),
                        "resolution": list(res_1),
                    }
                },
            )
            save_extrinsics(
                folder,
                cam_2,
                res_2,
                {
                    cam_1: {
                        "order": "second",
                        "rotation": R.tolist(),
                        "translation": T.tolist(),
                        "resolution": list(res_2),
                    }
                },
            )

    def _estimate_params(self):
        """ Estimate camera parameters. """
        resolutions, patterns = self._get_patterns()

        try:
            self._intrinsics_result = {}
            for camera in patterns:
                logger.debug(
                    f"Estimating intrinsics for camera {camera} "
                    f"with resolution {resolutions[camera]} "
                    f"and {self.distortion_model} distortion"
                )
                self._intrinsics_result[camera] = (
                    resolutions[camera],
                    self.distortion_model,
                    *calculate_intrinsics(
                        resolutions[camera], patterns[camera], self._obj_points
                    ),
                )
        except cv2.error as e:
            self._intrinsics_result = None
            logger.warning(
                f"Intrinsics estimation failed. Reason: {e}\n"
                f"Please try again with a better coverage of the camera's FOV!"
            )
            return

        # Skip saving intrinsics when estimating extrinsics because the
        # calibration data will most likely be poorer than when estimating
        # intrinsics for each stream individually
        if not self.estimate_extrinsics:
            self._save_intrinsics(self.folder, self._intrinsics_result)

        if self.estimate_extrinsics:
            try:
                self._extrinsics_result = {}
                for camera_1, camera_2 in combinations(patterns, 2):
                    logger.debug(
                        f"Estimating extrinsics for device pair "
                        f"({camera_1}, {camera_2}) with "
                        f"{self.distortion_model} distortion"
                    )
                    self._extrinsics_result[(camera_1, camera_2)] = (
                        resolutions[camera_1],
                        resolutions[camera_2],
                        *calculate_extrinsics(
                            patterns[camera_1],
                            patterns[camera_2],
                            self._obj_points,
                            self._intrinsics_result[camera_1][2],
                            self._intrinsics_result[camera_1][3],
                            self._intrinsics_result[camera_2][2],
                            self._intrinsics_result[camera_2][3],
                            self.distortion_model,
                        ),
                    )
            except cv2.error as e:
                self._extrinsics_result = None
                logger.warning(f"Extrinsics estimation failed. Reason: {e}")
                return

            self._save_extrinsics(self.folder, self._extrinsics_result)

        logger.info("Successfully estimated camera parameters")
