import pytest

from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import (
    BaseVideoDevice,
    VideoDeviceUVC,
)
from pupil_recording_interface.device.flir import VideoDeviceFLIR
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.errors import DeviceNotConnected, IllegalSetting


class TestBaseDevice:
    def test_from_config(self, video_stream_config):
        """"""
        assert isinstance(
            BaseDevice.from_config(video_stream_config), VideoDeviceUVC
        )


class TestBaseVideoDevice:
    def test_constructor(self):
        """"""
        device = BaseVideoDevice("Pupil Cam1 ID2", (1280, 720), 30)
        assert device.device_uid == "Pupil Cam1 ID2"
        assert device.resolution == (1280, 720)
        assert device.fps == 30


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
        capture = VideoDeviceUVC.get_capture(
            device_uid, (1280, 720), 30, {"Auto Exposure Mode": 1}
        )
        controls = {c.display_name: c.value for c in capture.controls}
        assert controls["Auto Exposure Mode"] == 1
        del capture

        with pytest.raises(IllegalSetting):
            VideoDeviceUVC.get_capture(device_uid, (1280, 720), 200)

    @pytest.mark.xfail(raises=DeviceNotConnected)
    @pytest.mark.parametrize(
        "device_uid", ["Pupil Cam1 ID2", "Pupil Cam2 ID2", "Pupil Cam3 ID2"]
    )
    def test_get_frame_and_timestamp(self, device_uid):
        """"""
        device = VideoDeviceUVC(device_uid, (1280, 720), 60)
        device.start()
        frame, ts = device.get_frame_and_timestamp()
        assert frame.shape == (720, 1280, 3)
        assert isinstance(ts, float)

        with pytest.raises(RuntimeError):
            VideoDeviceUVC(
                device_uid, (1280, 720), 60
            ).get_frame_and_timestamp()


class TestVideoDeviceFLIR:
    @pytest.fixture(autouse=True)
    def PySpin(self):
        """"""
        return pytest.importorskip("PySpin")

    @pytest.fixture(autouse=True)
    def simple_pyspin(self):
        """"""
        return pytest.importorskip("simple_pyspin")

    @pytest.mark.xfail(raises=DeviceNotConnected)
    def test_get_capture(self, simple_pyspin):
        """"""
        capture = VideoDeviceFLIR.get_capture(None, (2048, 1536), 30.0)
        assert isinstance(capture, simple_pyspin.Camera)
        capture.close()

        # custom settings
        VideoDeviceFLIR.get_capture(
            None,
            (2048, 1536),
            30.0,
            settings={
                "GainAuto": "Off",
                "Gain": 30.0,
                "ExposureAuto": "Off",
                "ExposureTime": 300.0,
            },
        )


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
