import os

import pytest

from pupil_recording_interface.cli import CLI


class TestCLI(object):

    def test_record(self):
        """"""
        # TODO test record odometry

        with pytest.raises(ValueError):
            CLI.record(['pri', 'record', 'not_a_topic', '.'])

    def test_export(self, folder):
        """"""
        # gaze
        CLI.export(['pri', 'export', 'gaze', folder])
        assert os.path.exists(
            os.path.join(folder, 'exports', 'gaze.nc'))

        # odometry
        CLI.export(['pri', 'export', 'odometry', folder])
        assert os.path.exists(
            os.path.join(folder, 'exports', 'odometry.nc'))

        # TODO test export video

        with pytest.raises(ValueError):
            CLI.export(['pri', 'export', 'not_a_topic', '.'])

    def test_run(self, folder):
        """"""
        CLI().run(['pri', 'export', 'gaze', folder])
        assert os.path.exists(
            os.path.join(folder, 'exports', 'gaze.nc'))
