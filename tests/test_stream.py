import time

import numpy as np
import pytest

from pupil_recording_interface.stream import BaseStream


class TestBaseStream:
    def test_constructor(self, mock_device):
        """"""
        stream = BaseStream(mock_device)
        assert stream.device is mock_device
        assert stream.name == "mock_device"

    def test_from_config(self, mock_stream_config, mock_device):
        """"""
        stream = BaseStream.from_config(mock_stream_config)
        assert stream.name == "mock_stream"
        assert isinstance(stream.device, type(mock_device))

        stream = BaseStream.from_config(mock_stream_config, device=mock_device)
        assert stream.name == "mock_stream"
        assert stream.device is mock_device

        mock_stream_config.stream_type = "unregistered_type"
        with pytest.raises(ValueError):
            BaseStream.from_config(mock_stream_config)

    def test_current_fps(self, mock_stream):
        """"""
        np.testing.assert_equal(mock_stream.current_fps, float("nan"))

        mock_stream._fps_buffer.append(1.0)
        mock_stream._fps_buffer.append(3.0)
        assert mock_stream.current_fps == 2.0

    def test_get_status(self, mock_stream, packet, monkeypatch):
        """"""
        monkeypatch.setattr(time, "time", lambda: 1.0)

        status = mock_stream.get_status()
        np.testing.assert_equal(
            status,
            {
                "device_uid": "mock_device",
                "fps": float("nan"),
                "last_source_timestamp": float("nan"),
                "name": "mock_stream",
                "running": False,
                "source_timestamp": float("nan"),
                "status_timestamp": 1.0,
                "timestamp": float("nan"),
            },
        )

        status = mock_stream.get_status(packet)
        np.testing.assert_equal(
            status,
            {
                "device_uid": "mock_device",
                "fps": float("nan"),
                "last_source_timestamp": float("nan"),
                "name": "mock_stream",
                "running": True,
                "source_timestamp": 0.0,
                "status_timestamp": 1.0,
                "timestamp": 0.0,
            },
        )

    def test_process_timestamp(self, mock_stream):
        """"""
        mock_stream._process_timestamp(1.0)
        assert mock_stream._last_source_timestamp == 1.0
        np.testing.assert_equal(mock_stream.current_fps, float("nan"))

        mock_stream._process_timestamp(1.0)
        np.testing.assert_equal(mock_stream.current_fps, float("nan"))

        mock_stream._process_timestamp(2.0)
        assert mock_stream._last_source_timestamp == 2.0
        assert mock_stream.current_fps == 1.0
