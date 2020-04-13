""""""
from queue import Queue, Full
import logging

import cv2
import numpy as np

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.methods import gen_pattern_grid

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

    def _get_resolution(self, packet):
        """"""
        frame = packet["frame"]

        if self.stereo:
            return frame.shape[1] // 2, frame.shape[0]
        else:
            return frame.shape[1::-1]

    def detect_grid(self, packet):
        """"""
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
            return grid_points
        else:
            return None

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.resolution = self.call(
            self._get_resolution, packet, block=block
        )
        packet.grid_points = self.call(self.detect_grid, packet, block=block)

        # TODO maybe don't broadcast on every single packet
        packet.broadcasts.append("resolution")
        packet.broadcasts.append("grid_points")

        return packet


@process("cam_param_estimator")
class CamParamEstimator(BaseProcess):
    """"""

    def __init__(
        self,
        streams,
        block=False,
        grid_shape=(4, 11),
        num_patterns=10,
        **kwargs,
    ):
        """ Constructor. """
        self.streams = streams
        self.num_patterns = num_patterns

        super().__init__(
            block=block, listen_for=["resolution", "grid_points"], **kwargs
        )

        self.intrinsics = None
        self.extrinsics = None

        self._obj_points = gen_pattern_grid(grid_shape)
        self._pattern_queue = Queue(maxsize=self.num_patterns)
        self._acquire_pattern = False

    def _add_pattern(self, grid_points):
        """"""
        self._pattern_queue.put(grid_points, False)
        logger.info(
            f"Captured pattern {self._pattern_queue.qsize()} of "
            f"{self.num_patterns}"
        )

        if self._pattern_queue.full():
            self._estimate_params()

    def _get_patterns(self):
        """ Get patterns from pattern queue by camera. """
        resolutions, patterns = {}, {}

        while not self._pattern_queue.empty():
            pattern = self._pattern_queue.get()

            for stream, (resolution, grid_points) in pattern.items():

                if isinstance(grid_points, list):
                    for idx, gp in enumerate(grid_points):
                        cam = f"{stream}_{idx}"
                        if cam not in resolutions:
                            resolutions[cam] = resolution
                        elif resolution != resolutions[cam]:
                            raise ValueError(
                                f"Got multiple resolutions for camera: {cam}"
                            )
                        if stream not in patterns:
                            patterns[cam] = []
                        patterns[cam].append(gp)

                else:
                    if stream not in resolutions:
                        resolutions[stream] = resolution
                    elif resolution != resolutions[stream]:
                        raise ValueError(
                            f"Got multiple resolutions for camera: {stream}"
                        )
                    if stream not in patterns:
                        patterns[stream] = []
                    patterns[stream].append(grid_points)

        return resolutions, patterns

    @classmethod
    def calculate_intrinsics(
        cls, resolution, img_points, obj_points, dist_mode="Fisheye"
    ):
        """ Calculate intrinsic parameters for one camera. """
        logger.debug(f"Calibrating camera with resolution: {resolution}")

        if dist_mode == "Fisheye":
            calibration_flags = (
                cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
                + cv2.fisheye.CALIB_CHECK_COND
                + cv2.fisheye.CALIB_FIX_SKEW
            )

            max_iter = 30
            eps = 1e-6

            camera_matrix = np.zeros((3, 3))
            dist_coefs = np.zeros((4, 1))
            count = len(img_points)
            rvecs = [
                np.zeros((1, 1, 3), dtype=np.float64) for _ in range(count)
            ]
            tvecs = [
                np.zeros((1, 1, 3), dtype=np.float64) for _ in range(count)
            ]
            obj_points = [obj_points.reshape(1, -1, 3) for _ in range(count)]

            try:
                rms, _, _, _, _ = cv2.fisheye.calibrate(
                    obj_points,
                    img_points,
                    resolution[::-1],
                    camera_matrix,
                    dist_coefs,
                    rvecs,
                    tvecs,
                    calibration_flags,
                    (
                        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                        max_iter,
                        eps,
                    ),
                )
            except cv2.error as e:
                logger.warning(f"Camera calibration failed. Reason: {e}")
                logger.warning(
                    "Please try again with a better coverage of the cameras "
                    "FOV!"
                )

            logger.debug(f"Calibrated Camera, RMS:{rms:.6f}")
            return camera_matrix, dist_coefs
        else:
            logger.error(f"Unkown distortion model: {dist_mode}")
            return None, None

    @classmethod
    def calculate_extrinsics(
        cls,
        img_points_a,
        img_points_b,
        obj_points,
        cam_mtx_a,
        dist_coefs_a,
        cam_mtx_b,
        dist_coefs_b,
    ):
        """ Calculate extrinsics for pairs of cameras. """
        img_points_left = np.array(
            [x.reshape(1, -1, 2) for x in img_points_a], dtype=np.float64
        )
        img_points_right = np.array(
            [x.reshape(1, -1, 2) for x in img_points_b], dtype=np.float64
        )
        obj_points = [
            obj_points.reshape(1, -1, 3) for _ in range(len(img_points_a))
        ]

        R = np.zeros((1, 1, 3), dtype=np.float64)
        T = np.zeros((1, 1, 3), dtype=np.float64)

        try:
            rms, _, _, _, _, R, T = cv2.fisheye.stereoCalibrate(
                obj_points,
                img_points_right,
                img_points_left,
                cam_mtx_a,
                dist_coefs_a,
                cam_mtx_b,
                dist_coefs_b,
                (0, 0),
                R,
                T,
                cv2.CALIB_FIX_INTRINSIC,
            )
        except cv2.error as e:
            logger.warning(f"Stereo calibration failed. Reason: {e}")

    def _estimate_params(self):
        """"""
        logger.debug("Estimating camera parameters")

        resolutions, patterns = self._get_patterns()

        self.intrinsics = {
            self.calculate_intrinsics(
                resolutions[camera], patterns[camera], self._obj_points
            )
            for camera in patterns
        }

        logger.info("Successfully estimated camera parameters")

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            if (
                "acquire_pattern" in notification
                and notification["acquire_pattern"]
            ):
                # TODO with Lock?
                self._acquire_pattern = True
            if self._acquire_pattern and all(
                stream in notification for stream in self.streams
            ):
                try:
                    pattern = {
                        "stream": (
                            notification[stream]["resolution"],
                            notification[stream]["grid_points"],
                        )
                        for stream in self.streams
                    }
                    # TODO with Lock?
                    self._acquire_pattern = False
                    self._add_pattern(pattern)
                except KeyError:
                    pass
                except Full:
                    break
