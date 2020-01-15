""""""
from collections import namedtuple

from pupil_recording_interface.recorder.video import BaseVideoCapture
from pupil_recording_interface.device.realsense import VideoDeviceT265


# TODO expand this into a class inheriting from BaseConfig?
RealSenseConfig = namedtuple(
    'RealSenseConfig', [
        'device_type', 'device_name', 'resolution', 'fps', 'color_format'])


class VideoCaptureT265(BaseVideoCapture, VideoDeviceT265):
    """"""


