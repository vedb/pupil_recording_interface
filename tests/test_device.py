import pytest

from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import VideoDeviceUVC
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.errors import DeviceNotConnected, IllegalSetting


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


class TestVideoDeviceUVC:
    @pytest.fixture(autouse=True)
    def uvc(self):
        """"""
        return pytest.importorskip("uvc")

    @pytest.mark.xfail(raises=DeviceNotConnected)
    @pytest.mark.parametrize(
        "device_uid", ["Pupil Cam1 ID2", "Pupil Cam2 ID2", "Pupil Cam3 ID2"]
    )
    def test_get_capture(self, device_uid):
        """"""
        capture = VideoDeviceUVC._get_capture(
            device_uid, (1280, 720), 30, {"Auto Exposure Mode": 1}
        )
        controls = {c.display_name: c.value for c in capture.controls}
        assert controls["Auto Exposure Mode"] == 1
        del capture

        with pytest.raises(IllegalSetting):
            VideoDeviceUVC._get_capture(device_uid, (1280, 720), 200)


class TestRealSenseDeviceT265:
    def test_from_config(self, video_stream_config, motion_stream_config):
        """"""
        video_stream_config.device_type = "t265"
        device = RealSenseDeviceT265.from_config(video_stream_config)
        assert device.video == "both"

        device = RealSenseDeviceT265.from_config(motion_stream_config)
        assert device.odometry

        motion_stream_config.motion_type = "accel"
        device = RealSenseDeviceT265.from_config(motion_stream_config)
        assert device.accel

        motion_stream_config.motion_type = "gyro"
        device = RealSenseDeviceT265.from_config(motion_stream_config)
        assert device.gyro

    def test_from_config_list(self, video_stream_config, motion_stream_config):
        """"""
        video_stream_config.device_type = "t265"
        config_list = [video_stream_config, motion_stream_config]

        device = RealSenseDeviceT265.from_config_list(config_list)

        assert isinstance(device, RealSenseDeviceT265)
        assert device.resolution == (1280, 720)
        assert device.fps == 30
        assert device.video == "both"
        assert device.odometry
