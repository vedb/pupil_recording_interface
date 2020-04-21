import pytest
import numpy as np

from pupil_recording_interface.manager import StreamManager


class TestManager:
    @pytest.mark.skip("Not yet implemented")
    def test_init_folder(self, temp_folder):
        """"""

    def test_get_status(self, stream_manager, packet):
        """"""
        status = stream_manager.streams["mock_stream"].get_status()
        stream_manager._status_queues["mock_stream"].append(status)

        np.testing.assert_equal(
            stream_manager._get_status(),
            {
                "mock_stream": {
                    "name": "mock_stream",
                    "device_uid": "mock_device",
                    "timestamp": float("nan"),
                    "source_timestamp": float("nan"),
                    "last_source_timestamp": float("nan"),
                    "running": False,
                    "fps": float("nan"),
                }
            },
        )

        status = stream_manager.streams["mock_stream"].get_status(packet)
        stream_manager._status_queues["mock_stream"].append(status)

        np.testing.assert_equal(
            stream_manager._get_status(),
            {
                "mock_stream": {
                    "name": "mock_stream",
                    "device_uid": "mock_device",
                    "timestamp": 0.0,
                    "source_timestamp": 0.0,
                    "last_source_timestamp": float("nan"),
                    "running": True,
                    "fps": float("nan"),
                }
            },
        )

        assert stream_manager._get_status() == {}

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
