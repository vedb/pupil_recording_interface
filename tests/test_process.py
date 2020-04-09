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

        # no gaze points
        display_packet.gaze_points = [(0.5, 0.5)]
        video_display._add_gaze_overlay(display_packet)

    def test_add_circle_grid_overlay(self, video_display, display_packet):
        """"""
        frame = video_display._add_circle_grid_overlay(display_packet)
        assert frame.ndim == 3
