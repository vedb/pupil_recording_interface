import pytest

from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import VideoDeviceUVC
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.stream import VideoStream, MotionStream


class TestBaseDevice:
    def test_from_config(self, video_stream_config):
        """"""
        assert isinstance(
            BaseDevice.from_config(video_stream_config), VideoDeviceUVC
        )


class TestBaseVideoDevice:
    @pytest.mark.skip("Not yet implemented")
    def test_start(self):
        """"""


class TestRealSenseDeviceT265:
    def test_from_config_list(self):
        """"""
        config_list = [
            VideoStream.Config(
                device_type="t265",
                device_uid="t265",
                resolution=(1696, 800),
                fps=30,
                color_format="gray",
            ),
            MotionStream.Config(
                device_type="t265", device_uid="t265", motion_type="odometry"
            ),
        ]

        device = RealSenseDeviceT265.from_config_list(config_list)

        assert isinstance(device, RealSenseDeviceT265)
        assert device.resolution == (1696, 800)
        assert device.fps == 30
        assert device.video == "both"
        assert device.odometry
