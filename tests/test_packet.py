import pytest

from pupil_recording_interface.packet import Packet


class TestPacket:
    def test_constructor(self):
        """"""
        packet = Packet(1.0)
        assert packet.timestamp == 1.0
        assert packet.source_timestamp == 1.0
        assert packet.source_timebase == "monotonic"

        packet = Packet(1.0, 2.0, "epoch", frame=None)
        assert packet.timestamp == 1.0
        assert packet.source_timestamp == 2.0
        assert packet.source_timebase == "epoch"
        assert packet.frame is None

        with pytest.raises(ValueError):
            Packet(1.0, source_timebase="not_a_timebase")

    @pytest.mark.skip("Not yet implemented")
    def test_to_dict(self):
        """"""
