import pytest

from pupil_recording_interface.decorators import device, stream, process
from pupil_recording_interface.device.video import VideoDeviceUVC
from pupil_recording_interface.device.flir import VideoDeviceFLIR
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.stream import VideoStream, OdometryStream
from pupil_recording_interface.process import (
    VideoDisplay,
    VideoRecorder,
    OdometryRecorder,
    PupilDetector,
    GazeMapper,
)


class TestDecorators:
    def test_device_decorator(self):
        """"""
        assert device.registry == {
            "uvc": VideoDeviceUVC,
            "flir": VideoDeviceFLIR,
            "t265": RealSenseDeviceT265,
        }

        # new device with same name raises error
        with pytest.raises(ValueError):
            device("uvc")(VideoDeviceUVC)

    def test_stream_decorator(self):
        """"""
        assert stream.registry == {
            "video": VideoStream,
            "odometry": OdometryStream,
        }

    def test_process_decorator(self):
        """"""
        assert process.registry == {
            "video_display": VideoDisplay,
            "video_recorder": VideoRecorder,
            "odometry_recorder": OdometryRecorder,
            "pupil_detector": PupilDetector,
            "gaze_mapper": GazeMapper,
        }
