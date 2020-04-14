""""""
from itertools import combinations
from queue import Queue, Full
from threading import Lock
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.utils import get_constructor_args
from pupil_recording_interface.externals.methods import gen_pattern_grid
from pupil_recording_interface.externals.file_methods import save_intrinsics

logger = logging.getLogger(__name__)


@process("circle_grid_detector")
class CircleGridDetector(BaseProcess):
    """ Detector for circle grids. """

    def __init__(
        self, grid_shape=(4, 11), stereo=False, block=False, **kwargs
    ):
        """ Constructor. """
        self.grid_shape = grid_shape
        self.stereo = stereo

        super().__init__(block=block, **kwargs)

    def detect_grid(self, packet):
        """ Detect circle grid in frame. """
        frame = packet["frame"]

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

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.circle_grid = self.call(self.detect_grid, packet, block=block)

        # TODO maybe don't broadcast on every single packet
        packet.broadcasts.append("circle_grid")

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
    """"""

    def __init__(
        self,
        streams,
        folder,
        block=False,
        grid_shape=(4, 11),
        num_patterns=10,
        distortion_model="radial",
        extrinsics=False,
        **kwargs,
    ):
        """ Constructor. """
        self.streams = streams
        self.folder = folder
        self.num_patterns = num_patterns
        self.distortion_model = distortion_model
        self.extrinsics = extrinsics

        super().__init__(block=block, listen_for=["circle_grid"], **kwargs)

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
        cls_kwargs = get_constructor_args(
            cls, config, folder=config.folder or kwargs.get("folder", None),
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
        # TODO get device_uid
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

        self._save_intrinsics(self.folder, self.intrinsics)

        if self.extrinsics:
            try:
                self.extrinsics = {
                    (camera_1, camera_2): calculate_extrinsics(
                        patterns[camera_1],
                        patterns[camera_2],
                        self._obj_points,
                        self.intrinsics[camera_1][0],
                        self.intrinsics[camera_1][1],
                        self.intrinsics[camera_2][0],
                        self.intrinsics[camera_2][1],
                    )
                    for camera_1, camera_2 in combinations(patterns, 2)
                }
            except cv2.error as e:
                logger.warning(f"Extrinsics estimation failed. Reason: {e}")
                return

        logger.info("Successfully estimated camera parameters")

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            if (
                "acquire_pattern" in notification
                and notification["acquire_pattern"]
            ):
                self._acquire_pattern = True
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
            packet.broadcasts.append("pattern_acquired")
            self._pattern_acquired = False

        return packet
