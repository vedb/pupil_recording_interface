import pytest

from pupil_recording_interface.device.realsense import RealSenseDeviceT265


class TestRealSenseDeviceT265(object):

    def test_from_config_list(self):
        """"""
        from pupil_recording_interface.config import \
            VideoConfig, OdometryConfig

        config_list = [
            VideoConfig(
                't265', 't265',
                resolution=(1696, 800), fps=30, color_format='gray'),
            OdometryConfig(
                't265', 't265', name='odometry')
        ]

        RealSenseDeviceT265.from_config_list(config_list, start=False)
