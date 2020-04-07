import pytest

from pupil_recording_interface.base import BaseConfigurable


@pytest.fixture()
def configurable():
    class Configurable(BaseConfigurable):

        _config_attrs = {"configurable_type": "test"}
        _ignore_args = ("arg3",)
        _additional_args = ("arg2",)
        _optional_args = ("arg4",)

        def __init__(self, arg1, arg3, arg4, kwarg1=1, kwarg2=2):
            self.arg1 = arg1
            self.arg3 = arg3
            self.arg4 = arg4
            self.kwarg1 = kwarg1
            self.kwarg2 = kwarg2

    return Configurable


class TestBaseConfigurable:
    def test_config(self, configurable):
        """"""
        config = configurable.Config("a", "b", kwarg1=2)
        assert config.configurable_type == "test"
        assert config.arg1 == "a"
        assert config.arg2 == "b"
        assert config.arg4 is None
        assert config.kwarg1 == 2
        assert config.kwarg2 == 2

        config = configurable.Config(arg1="a", arg2="b")
        assert config.arg1 == "a"
        assert config.arg2 == "b"

        with pytest.raises(TypeError):
            configurable.Config(arg1="a")
