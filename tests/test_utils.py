from pupil_recording_interface.utils import (
    get_params,
    get_constructor_args,
    multiprocessing_deque,
)
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

        # regression test for overriding parameters with "False"
        video_config.fps = False
        assert get_constructor_args(BaseVideoDevice, video_config) == {
            "device_uid": "test_cam",
            "resolution": (1280, 720),
            "fps": False,
        }

    def test_multiprocessing_deque(self):
        """"""
        max_len = 10
        test_len = 12
        deque = multiprocessing_deque(max_len)
        for it in range(test_len):
            deque.append(it)

        for it in range(test_len - 1, test_len - max_len - 1, -1):
            assert deque.pop() == it

        assert not deque._getvalue()
