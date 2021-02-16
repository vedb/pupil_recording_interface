import pytest
import numpy as np

from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import (
    BaseVideoDevice,
    VideoDeviceUVC,
)
from pupil_recording_interface.device.flir import VideoDeviceFLIR
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.errors import DeviceNotConnected, IllegalSetting


class TestBaseDevice:
    def test_from_config(self, mock_stream_config, mock_device):
        """"""
        assert isinstance(
            BaseDevice.from_config(mock_stream_config), type(mock_device)
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

    def test_exposure_mode(self):
        """"""
        # 1st gen
        device = VideoDeviceUVC("Pupil Cam1 ID0", (320, 240), 120)
        assert device.exposure_handler is None

        # 2nd gen
        device = VideoDeviceUVC("Pupil Cam2 ID0", (192, 192), 120)
        assert device.exposure_handler is not None

        # 1st gen & forced
        device = VideoDeviceUVC(
            "Pupil Cam1 ID0", (320, 240), 120, exposure_mode="forced_auto"
        )
        assert device.exposure_handler is not None

        # manual
        device = VideoDeviceUVC(
            "Pupil Cam2 ID0", (192, 192), 120, exposure_mode="manual"
        )
        assert device.exposure_handler is None

    @pytest.mark.xfail(raises=DeviceNotConnected)
    @pytest.mark.parametrize(
        "device_uid", ["Pupil Cam1 ID2", "Pupil Cam2 ID2", "Pupil Cam3 ID2"]
    )
    def test_get_capture(self, device_uid):
        """"""
        capture = VideoDeviceUVC.get_capture(
            device_uid, (1280, 720), 30, {"Gamma": 200}
        )
        controls = {c.display_name: c.value for c in capture.controls}
        assert controls["Gamma"] == 200
        del capture

        with pytest.raises(IllegalSetting):
            VideoDeviceUVC.get_capture(device_uid, (1280, 720), 200)

    @pytest.mark.xfail(raises=DeviceNotConnected)
    @pytest.mark.parametrize(
        "device_uid", ["Pupil Cam1 ID2", "Pupil Cam2 ID2", "Pupil Cam3 ID2"]
    )
    def test_controls(self, device_uid):
        """"""
        device = VideoDeviceUVC(device_uid, (1280, 720), 60)

        # legal value
        with device:
            device.controls = {"Gamma": 100}
            device.controls = {"Gamma": 200}
            assert device.controls["Gamma"] == 200

        # illegal value
        with device:
            with pytest.raises(IllegalSetting):
                device.controls = {"Gamma": 0}

        # illegal name
        with device:
            with pytest.raises(IllegalSetting):
                device.controls = {"Beta": 0}

    @pytest.mark.xfail(raises=DeviceNotConnected)
    @pytest.mark.parametrize(
        "device_uid", ["Pupil Cam1 ID2", "Pupil Cam2 ID2", "Pupil Cam3 ID2"]
    )
    def test_get_frame_and_timestamp(self, device_uid):
        """"""
        device = VideoDeviceUVC(device_uid, (1280, 720), 60)
        with device:
            frame, ts = device.get_frame_and_timestamp()
            assert frame.shape == (720, 1280, 3)
            assert isinstance(ts, float)


class TestVideoFileDevice:
    def test_set_frame_index(self, video_file_device):
        """"""
        with video_file_device:
            _, file_ts, _ = video_file_device.get_frame_and_timestamp()
            assert file_ts == 1570725800.2383718
            video_file_device.set_frame_index(0)
            _, file_ts, _ = video_file_device.get_frame_and_timestamp()
            assert file_ts == 1570725800.2383718

    def test_get_frame_and_timestamp(self, video_file_device):
        """"""
        with video_file_device:
            frame, _, _ = video_file_device.get_frame_and_timestamp()
            assert frame.shape == (720, 1280, 3)

        file_ts = np.zeros(100)
        pb_ts = np.zeros(100)
        with video_file_device:
            for idx in range(100):
                (
                    _,
                    file_ts[idx],
                    pb_ts[idx],
                ) = video_file_device.get_frame_and_timestamp()

        assert np.median(np.abs(np.diff(pb_ts) - np.diff(file_ts))) < 1e-3


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
                "Gain": 15.0,
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
