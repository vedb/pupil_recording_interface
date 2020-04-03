import pytest

from pupil_recording_interface.stream import Packet


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


class TestBaseStream:
    @pytest.mark.skip("Not yet implemented")
    def test_constructor(self):
        """"""

    @pytest.mark.skip("Not yet implemented")
    def test_from_config(self, folder):
        """"""

    @pytest.mark.skip("Not yet implemented")
    def test_current_fps(self):
        """"""

    @pytest.mark.skip("Not yet implemented")
    def test_process_timestamp(self):
        """"""

    @pytest.mark.skip("Not yet implemented")
    def test_run_in_thread(self):
        """"""
