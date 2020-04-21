import pytest

from pupil_recording_interface.decorators import device, stream, process
from pupil_recording_interface.device.video import VideoDeviceUVC
from pupil_recording_interface.stream import VideoStream
from pupil_recording_interface.process.display import VideoDisplay


class TestDecorators:
    def test_device_decorator(self):
        """"""
        assert device.registry["uvc"] == VideoDeviceUVC

        # new device with same name raises error
        with pytest.raises(ValueError):
            device("uvc")(VideoDeviceUVC)

    def test_stream_decorator(self):
        """"""
        assert stream.registry["video"] == VideoStream

    def test_process_decorator(self):
        """"""
        assert process.registry["video_display"] == VideoDisplay
