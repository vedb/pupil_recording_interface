from pupil_recording_interface.utils import get_params, get_constructor_args
from pupil_recording_interface.device.video import BaseVideoDevice


class TestUtils:
    def test_get_params(self):
        """"""
        assert get_params(BaseVideoDevice) == (
            ["device_uid", "resolution", "fps"],
            {},
        )

    def test_get_constructor_args(self, video_config):
        """"""
        assert get_constructor_args(BaseVideoDevice, video_config) == {
            "device_uid": "test_cam",
            "resolution": (1280, 720),
            "fps": 30,
        }
