import pytest

from pupil_recording_interface.packet import Packet


class TestPacket:
    def test_constructor(self):
        """"""
        packet = Packet("stream_name", "device_uid", 1.0)
        assert packet.stream_name == "stream_name"
        assert packet.device_uid == "device_uid"
        assert packet.timestamp == 1.0
        assert packet.source_timestamp == 1.0
        assert packet.source_timebase == "monotonic"

        packet = Packet(
            "stream_name", "device_uid", 1.0, 2.0, "epoch", frame=None
        )
        assert packet.timestamp == 1.0
        assert packet.source_timestamp == 2.0
        assert packet.source_timebase == "epoch"
        assert packet.frame is None

        with pytest.raises(ValueError):
            Packet(
                "stream_name",
                "device_uid",
                1.0,
                source_timebase="not_a_timebase",
            )
