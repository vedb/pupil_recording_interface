import pytest
import numpy as np

from pupil_recording_interface.packet import Packet


@pytest.fixture()
def display_packet():
    """"""
    return Packet(
        0.0,
        frame=np.zeros((1280, 720), dtype=np.uint8),
        display_frame=np.zeros((1280, 720), dtype=np.uint8),
        pupil={
            "ellipse": {
                "center": (0.0, 0.0),
                "axes": (0.0, 0.0),
                "angle": -90.0,
            },
            "diameter": 0.0,
            "location": (0.0, 0.0),
            "confidence": 0.0,
        },
        gaze_points=[(0.5, 0.5), (0.6, 0.6)],
        circle_markers=[
            {
                "ellipses": [
                    (
                        (399.16404724121094, 215.4773941040039),
                        (7.052967071533203, 8.333015441894531),
                        43.05573272705078,
                    ),
                    (
                        (399.69960021972656, 215.33668518066406),
                        (53.05698776245117, 67.6202621459961),
                        8.497730255126953,
                    ),
                    (
                        (400.78492736816406, 215.5298080444336),
                        (109.97621154785156, 137.57115173339844),
                        8.513727188110352,
                    ),
                    (
                        (402.8581237792969, 215.88968658447266),
                        (170.45883178710938, 213.98965454101562),
                        8.824980735778809,
                    ),
                ],
                "img_pos": (399.16404724121094, 215.4773941040039),
                "norm_pos": (0.31184691190719604, 0.7007258415222168),
                "marker_type": "Ref",
            }
        ],
        grid_points=np.array(
            [
                [[100.0, 100.0]],
                [[100.0, 200.0]],
                [[200.0, 100.0]],
                [[200.0, 200.0]],
            ],
            dtype=np.float32,
        ),
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
    def test_add_pupil_overlay(self, video_display, display_packet):
        """"""
        frame = video_display._add_pupil_overlay(display_packet)
        assert frame.ndim == 3

    def test_add_gaze_overlay(self, video_display, display_packet):
        """"""
        frame = video_display._add_gaze_overlay(display_packet)
        assert frame.ndim == 3

        # no gaze points
        display_packet.gaze_points = []
        video_display._add_gaze_overlay(display_packet)

        # one gaze point
        display_packet.gaze_points = [(0.5, 0.5)]
        video_display._add_gaze_overlay(display_packet)

    def test_add_circle_grid_overlay(self, video_display, display_packet):
        """"""
        frame = video_display._add_circle_grid_overlay(display_packet)
        assert frame.ndim == 3

        # multiple grids
        display_packet.grid_points = [display_packet.grid_points] * 2
        video_display._add_circle_grid_overlay(display_packet)

        # no grid
        display_packet.grid_points = None
        video_display._add_circle_grid_overlay(display_packet)

    def test_add_circle_marker_overlay(self, video_display, display_packet):
        """"""
        frame = video_display._add_circle_marker_overlay(display_packet)
        assert frame.ndim == 3
