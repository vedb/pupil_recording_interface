import pytest

from pupil_recording_interface.manager import StreamManager


class TestManager:
    @pytest.mark.skip("Not yet implemented")
    def test_init_folder(self, folder):
        """"""

    def test_get_notifications(self, statuses, video_stream):
        """"""
        video_stream.pipeline.steps[0].listen_for = ["pupil"]
        assert StreamManager._get_notifications(statuses, video_stream) == {
            "eye0": {
                "name": "eye0",
                "device_uid": "Pupil Cam1 ID0",
                "timestamp": 1.0,
                "pupil": {
                    "ellipse": {
                        "center": (0.0, 0.0),
                        "axes": (0.0, 0.0),
                        "angle": -90.0,
                    },
                    "diameter": 0.0,
                    "location": (0.0, 0.0),
                    "confidence": 0.0,
                },
            }
        }
