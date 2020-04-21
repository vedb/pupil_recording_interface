import pytest

from pupil_recording_interface.base import BaseConfigurable
from pupil_recording_interface.device.video import BaseVideoDevice


@pytest.fixture()
def configurable():
    class Configurable(BaseConfigurable):

        _config_attrs = {"configurable_type": "test"}
        _ignore_args = ("arg3",)
        _additional_args = ("arg2",)
        _additional_kwargs = {"kwarg3": 1}
        _optional_args = ("arg4",)

        def __init__(self, arg1, arg3, arg4, kwarg1=1, kwarg2=2):
            self.arg1 = arg1
            self.arg3 = arg3
            self.arg4 = arg4
            self.kwarg1 = kwarg1
            self.kwarg2 = kwarg2

    return Configurable


class TestBaseConfigurable:
    def test_get_params(self):
        """"""
        assert BaseVideoDevice.get_params() == (
            ["device_uid", "resolution", "fps"],
            {},
        )

    def test_get_constructor_args(self, video_stream_config):
        """"""
        assert BaseVideoDevice.get_constructor_args(video_stream_config) == {
            "device_uid": "test_cam",
            "resolution": (1280, 720),
            "fps": 30,
        }

        # regression test for overriding parameters with "False"
        video_stream_config.fps = False
        assert BaseVideoDevice.get_constructor_args(video_stream_config) == {
            "device_uid": "test_cam",
            "resolution": (1280, 720),
            "fps": False,
        }

    def test_config(self, configurable):
        """"""
        config = configurable.Config("a", "b", kwarg1=2)
        assert config.configurable_type == "test"
        assert config.arg1 == "a"
        assert config.arg2 == "b"
        assert config.arg4 is None
        assert config.kwarg1 == 2
        assert config.kwarg2 == 2
        assert config.kwarg3 == 1

        config = configurable.Config(arg1="a", arg2="b")
        assert config.arg1 == "a"
        assert config.arg2 == "b"

        # regression test for optional args being overwritten with None
        config = configurable.Config("a", "b", arg4="test")
        assert config.arg4 == "test"

        with pytest.raises(TypeError):
            configurable.Config(arg1="a")
