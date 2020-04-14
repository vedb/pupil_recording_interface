import os

import pytest
import numpy as np

from pupil_recording_interface.process.cam_params import (
    calculate_intrinsics,
    calculate_extrinsics,
)
from pupil_recording_interface.externals.file_methods import (
    load_object,
    load_pldata_file,
)


class TestVideoRecorder:
    @pytest.mark.skip("Not yet implemented")
    def test_from_config(self, folder):
        """"""

    @pytest.mark.skip("Not yet implemented")
    def test_get_data_and_timestamp(self):
        """"""

    @pytest.mark.skip("Not yet implemented")
    def test_stop(self):
        """"""


class TestOdometryRecorder:
    @pytest.mark.skip("Not yet implemented")
    def test_from_config(self, folder):
        """"""


class TestVideoDisplay:
    def test_add_pupil_overlay(self, video_display, packet):
        """"""
        frame = video_display._add_pupil_overlay(packet)
        assert frame.ndim == 3

    def test_add_gaze_overlay(self, video_display, packet):
        """"""
        frame = video_display._add_gaze_overlay(packet)
        assert frame.ndim == 3

        # no gaze points
        packet.gaze_points = []
        video_display._add_gaze_overlay(packet)

        # one gaze point
        packet.gaze_points = [(0.5, 0.5)]
        video_display._add_gaze_overlay(packet)

    def test_add_circle_grid_overlay(self, video_display, packet):
        """"""
        frame = video_display._add_circle_grid_overlay(packet)
        assert frame.ndim == 3

        # multiple grids
        packet.circle_grid["grid_points"] = [
            packet.circle_grid["grid_points"]
        ] * 2
        video_display._add_circle_grid_overlay(packet)

        # no grid
        packet.circle_grid = None
        video_display._add_circle_grid_overlay(packet)

    def test_add_circle_marker_overlay(self, video_display, packet):
        """"""
        frame = video_display._add_circle_marker_overlay(packet)
        assert frame.ndim == 3


class TestPupilDetector:
    def test_record_data(self, pupil_detector, packet):
        """"""
        packet.device_uid = "Pupil Cam1 ID0"
        pupil_detector.record_data(packet)
        pupil_detector.stop()

        pldata = [
            dict(d)
            for d in load_pldata_file(pupil_detector.folder, "pupil").data
        ]

        assert pldata[0] == {
            "ellipse": {
                "center": (0.0, 0.0),
                "axes": (0.0, 0.0),
                "angle": -90.0,
            },
            "diameter": 0.0,
            "location": (0.0, 0.0),
            "confidence": 0.0,
            "norm_pos": (0.0, 0.0),
            "timestamp": 0.0,
            "topic": "pupil.0",
            "id": 0,
            "method": "2d c++",
        }


class TestCamParamEstimator:
    def test_get_patterns(self, cam_param_estimator, packet):
        """"""
        resolutions, patterns = cam_param_estimator._get_patterns()

        assert resolutions == {
            "world": (1280, 720),
            "t265_left": (848, 800),
            "t265_right": (848, 800),
        }

        assert patterns.keys() == {"world", "t265_left", "t265_right"}
        np.testing.assert_equal(
            patterns["world"], [packet.circle_grid["grid_points"]] * 2
        )
        np.testing.assert_equal(
            patterns["t265_left"], [packet.circle_grid["grid_points"]] * 2
        )
        np.testing.assert_equal(
            patterns["t265_right"], [packet.circle_grid["grid_points"]] * 2
        )

    def test_calculate_intrinsics(self, cam_param_estimator, patterns):
        """"""
        # Pupil world cam
        cam_mtx, dist_coefs = calculate_intrinsics(
            (1280, 720), patterns["world"], cam_param_estimator._obj_points
        )
        assert cam_mtx.shape == (3, 3)
        assert dist_coefs.shape == (1, 5)

        # T265
        cam_mtx, dist_coefs = calculate_intrinsics(
            (848, 800),
            patterns["t265_left"],
            cam_param_estimator._obj_points,
            dist_mode="fisheye",
        )
        assert cam_mtx.shape == (3, 3)
        assert dist_coefs.shape == (4, 1)

        cam_mtx, dist_coefs = calculate_intrinsics(
            (848, 800),
            patterns["t265_right"],
            cam_param_estimator._obj_points,
            dist_mode="fisheye",
        )
        assert cam_mtx.shape == (3, 3)
        assert dist_coefs.shape == (4, 1)

    def test_calculate_extrinsics(self, cam_param_estimator, patterns):
        """"""
        cam_mtx_a, dist_coefs_a = calculate_intrinsics(
            (848, 800),
            patterns["t265_left"],
            cam_param_estimator._obj_points,
            dist_mode="fisheye",
        )

        cam_mtx_b, dist_coefs_b = calculate_intrinsics(
            (848, 800),
            patterns["t265_right"],
            cam_param_estimator._obj_points,
            dist_mode="fisheye",
        )

        R, T = calculate_extrinsics(
            patterns["t265_left"],
            patterns["t265_right"],
            cam_param_estimator._obj_points,
            cam_mtx_a,
            dist_coefs_a,
            cam_mtx_b,
            dist_coefs_b,
            dist_mode="fisheye",
        )

        np.testing.assert_allclose(R, np.eye(3), atol=0.02, rtol=1e-4)
        assert T.shape == (3, 1)

    def test_save_intrinsics(self, cam_param_estimator, intrinsics):
        """"""
        cam_param_estimator._save_intrinsics(
            cam_param_estimator.folder, intrinsics
        )
        intrinsics = load_object(
            os.path.join(cam_param_estimator.folder, "world.intrinsics")
        )
        assert intrinsics["(1280, 720)"] == {
            "camera_matrix": [
                [1091.0284, 0.0, 540.758028],
                [0.0, 906.409752, 448.742036],
                [0.0, 0.0, 1.0],
            ],
            "dist_coefs": [
                [-0.59883649, 0.54028932, -0.03402168, 0.03306559, -0.3829259]
            ],
            "cam_type": "radial",
            "resolution": [1280, 720],
        }
