import pytest
import numpy as np


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
        packet.grid_points = [packet.grid_points] * 2
        video_display._add_circle_grid_overlay(packet)

        # no grid
        packet.grid_points = None
        video_display._add_circle_grid_overlay(packet)

    def test_add_circle_marker_overlay(self, video_display, packet):
        """"""
        frame = video_display._add_circle_marker_overlay(packet)
        assert frame.ndim == 3


class TestCamParamEstimator:
    def test_get_patterns(self, cam_param_estimator, packet):
        """"""
        resolutions, patterns = cam_param_estimator._get_patterns()

        assert resolutions == {
            "world": (1280, 720),
            "t265_0": (1280, 720),
            "t265_1": (1280, 720),
        }

        assert patterns.keys() == {"world", "t265_0", "t265_1"}
        np.testing.assert_equal(patterns["world"], [packet.grid_points])
        np.testing.assert_equal(patterns["t265_0"], [packet.grid_points])
        np.testing.assert_equal(patterns["t265_1"], [packet.grid_points])
