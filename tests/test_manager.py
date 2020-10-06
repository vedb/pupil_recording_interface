import time

import numpy as np
import pytest

from pupil_recording_interface import __version__
from pupil_recording_interface.manager import StreamManager


class TestManager:
    def test_init_folder(self, tmpdir):
        """"""
        folder = StreamManager._init_folder(tmpdir, "here")
        assert folder == tmpdir

        folder = StreamManager._init_folder(tmpdir, "read")
        assert folder == tmpdir

        folder = StreamManager._init_folder(tmpdir, "new_folder")
        assert folder == tmpdir / "000"
        assert folder.exists()

        folder = StreamManager._init_folder(tmpdir, "overwrite")
        assert folder == tmpdir
        assert not (folder / "000").exists()

        with pytest.raises(ValueError):
            StreamManager._init_folder(tmpdir, "not_a_policy")

    def test_get_status(self, stream_manager, packet, monkeypatch):
        """"""
        monkeypatch.setattr(time, "time", lambda: 1.0)

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
                    "status_timestamp": 1.0,
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
                    "status_timestamp": 1.0,
                    "running": True,
                    "fps": float("nan"),
                }
            },
        )

        assert stream_manager._get_status() == {}

    def test_update_status(self, stream_manager):
        """"""

        # default status
        stream_manager._update_status({})
        np.testing.assert_equal(
            stream_manager.status["mock_stream"]["timestamp"], float("nan")
        )

        # updated status
        stream_manager._update_status({"mock_stream": {"timestamp": 1.0}})
        assert stream_manager.status["mock_stream"]["timestamp"] == 1.0

        # status too old
        stream_manager.status_timeout = 0.1
        time.sleep(0.1)
        stream_manager._update_status({})
        np.testing.assert_equal(
            stream_manager.status["mock_stream"]["timestamp"], float("nan")
        )

    def test_format_status(self, stream_manager, statuses):
        """"""
        stream_manager.status = statuses
        assert (
            stream_manager.format_status("fps") == "eye0: 120.00, world: 30.00"
        )
        assert (
            stream_manager.format_status("fps", max_cols=17)
            == "eye0: 120.00, ..."
        )

        stream_manager.status["world"]["fps"] = np.nan
        assert (
            stream_manager.format_status("fps")
            == "eye0: 120.00, world: no data"
        )
        assert (
            stream_manager.format_status("fps", nan_format=None)
            == "eye0: 120.00, world: nan"
        )

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

    def test_save_info(self, mock_stream_config, tmpdir):
        """"""
        import json

        manager = StreamManager(
            [mock_stream_config], folder=tmpdir, policy="here"
        )

        manager.save_info()
        with open(tmpdir / "info.player.json") as f:
            info = json.load(f)

        assert info["recording_name"] == str(tmpdir)
        assert info["recording_software_name"] == "pupil_recording_interface"
        assert info["recording_software_version"] == __version__

        # external app info
        manager = StreamManager(
            [mock_stream_config],
            folder=tmpdir,
            policy="here",
            app_info={"name": "parent_app", "version": "1.0.0"},
        )

        manager.save_info()
        with open(tmpdir / "info.player.json") as f:
            info = json.load(f)

        assert info["recording_software_name"] == "parent_app"
        assert info["recording_software_version"] == "1.0.0"
