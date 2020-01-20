import pytest

from pupil_recording_interface.recorder import BaseRecorder, BaseStreamRecorder
from pupil_recording_interface.recorder.video import \
    VideoEncoderFFMPEG, VideoRecorder
from pupil_recording_interface.recorder.odometry import OdometryRecorder
from pupil_recording_interface.recorder.multi_stream import MultiStreamRecorder


class TestBaseRecorder(object):

    def test_init_folder(self, folder):
        """"""


class TestBaseStreamRecorder(object):

    def test_from_config(self, output_folder, t265_config):
        """"""
        recorder = BaseStreamRecorder.from_config(
            t265_config[0], output_folder)
        assert isinstance(recorder, VideoRecorder)

        recorder = BaseStreamRecorder.from_config(
            t265_config[1], output_folder)
        assert isinstance(recorder, OdometryRecorder)

    def test_current_fps(self):
        """"""

    def test_process_timestamp(self):
        """"""

    def test_run_in_thread(self):
        """"""


class TestVideoEncoder(object):

    def test_get_ffmpeg_cmd(self):
        """"""


class TestVideoRecorder(object):

    def test_from_config(self, output_folder, t265_config):
        """"""
        recorder = VideoRecorder.from_config(t265_config[0], output_folder)
        assert isinstance(recorder, VideoRecorder)

    def test_get_data_and_timestamp(self):
        """"""

    def test_stop(self):
        """"""


class TestOdometryRecorder(object):

    def test_from_config(self, output_folder, t265_config):
        """"""
        recorder = OdometryRecorder.from_config(t265_config[1], output_folder)
        assert isinstance(recorder, OdometryRecorder)


class TestMultiStreamRecorder(object):

    def test_constructor(self, output_folder, t265_config):
        """"""
        recorder = MultiStreamRecorder(output_folder, t265_config)
        assert len(recorder.recorders) == 2
