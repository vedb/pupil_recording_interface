from pupil_recording_interface.device.realsense import RealSenseDeviceT265


class TestBaseVideoDevice(object):

    def test_start(self):
        """"""


class TestRealSenseDeviceT265(object):

    def test_from_config_list(self, t265_config):
        """"""
        device = RealSenseDeviceT265.from_config_list(t265_config)

        assert isinstance(device, RealSenseDeviceT265)
        assert device.resolution == (1696, 800)
        assert device.fps == 30
        assert device.video == 'both'
        assert device.odometry
