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
    def test_add_pupil_overlay(self, video_display, pupil_packet):
        """"""
        frame = video_display._add_pupil_overlay(pupil_packet)
        assert frame.ndim == 3

    def test_add_gaze_overlay(self, video_display, gaze_packet):
        """"""
        frame = video_display._add_gaze_overlay(gaze_packet)
        assert frame.ndim == 3

        # one gaze point
        gaze_packet.gaze = [gaze_packet.gaze[0]]
        video_display._add_gaze_overlay(gaze_packet)

        # no gaze points
        gaze_packet.gaze = []
        video_display._add_gaze_overlay(gaze_packet)

    def test_add_circle_grid_overlay(self, video_display, circle_grid_packet):
        """"""
        frame = video_display._add_circle_grid_overlay(circle_grid_packet)
        assert frame.ndim == 3

        # multiple grids
        circle_grid_packet.circle_grid["grid_points"] = [
            circle_grid_packet.circle_grid["grid_points"]
        ] * 2
        video_display._add_circle_grid_overlay(circle_grid_packet)

        # no grid
        circle_grid_packet.circle_grid = None
        video_display._add_circle_grid_overlay(circle_grid_packet)

    def test_add_circle_marker_overlay(
        self, video_display, circle_marker_packet
    ):
        """"""
        frame = video_display._add_circle_marker_overlay(circle_marker_packet)
        assert frame.ndim == 3


class TestPupilDetector:
    def test_record_data(self, pupil_detector, pupil_packet):
        """"""
        pupil_packet.device_uid = "Pupil Cam1 ID0"
        pupil_detector.record_data(pupil_packet)
        pupil_detector.stop()

        pldata = [
            dict(d)
            for d in load_pldata_file(pupil_detector.folder, "pupil").data
        ]

        assert pldata[0] == pupil_packet.pupil


class TestGazeMapper:
    def test_map_gaze(self, gaze_mapper, gaze_2d):
        """"""
        for g in gaze_2d:
            if len(g["base_data"]) == 2:
                mapped = gaze_mapper.map_gaze(
                    g["base_data"][0], g["base_data"][1],
                )
            elif g["base_data"][0]["id"] == 0:
                mapped = gaze_mapper.map_gaze(g["base_data"][0], None)
            else:
                mapped = gaze_mapper.map_gaze(None, g["base_data"][0])

            np.testing.assert_equal(mapped, g)

    def test_record_data(self, gaze_mapper, gaze_packet):
        """"""
        gaze_mapper.record_data(gaze_packet)
        gaze_mapper.stop()

        pldata = [
            dict(d) for d in load_pldata_file(gaze_mapper.folder, "gaze").data
        ]

        pldata[0].pop("base_data")

        assert pldata[0] == {
            "topic": "gaze.2d.01.",
            "norm_pos": (0.4629928051354275, 0.535180803465634),
            "confidence": 0.9748326882542296,
            "timestamp": 2295.232966,
        }


class TestCalibration:
    def test_calculate_calibration(
        self, calibration, pupil, reference_locations, calibration_2d
    ):
        """"""
        for p in pupil:
            calibration._pupil_queue.put(p)

        for r in reference_locations:
            calibration._circle_marker_queue.put(r)

        calibration.calculate_calibration()

        for param, actual in calibration.result["args"].items():
            expected = calibration_2d["data"][8][1][param]
            np.testing.assert_allclose(actual[:2], expected[:2])


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
