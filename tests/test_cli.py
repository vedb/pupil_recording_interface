import os

from .test_base import ReaderTester

from pupil_recording_interface.cli import CLI


class TestCLI(ReaderTester):

    def test_record(self):
        """"""
        # TODO test record odometry

        with self.assertRaises(ValueError):
            CLI.record(['pri', 'record', 'not_a_topic', '.'])

    def test_export(self):
        """"""
        # gaze
        CLI.export(['pri', 'export', 'gaze', self.folder])
        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'gaze.nc'))

        # odometry
        CLI.export(['pri', 'export', 'odometry', self.folder])
        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'odometry.nc'))

        # TODO test export video

        with self.assertRaises(ValueError):
            CLI.export(['pri', 'export', 'not_a_topic', '.'])

    def test_run(self):
        """"""
        CLI().run(['pri', 'export', 'gaze', self.folder])
        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'gaze.nc'))
