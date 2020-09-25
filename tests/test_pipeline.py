from pupil_recording_interface.pipeline import Pipeline
from pupil_recording_interface.process.recorder import VideoRecorder


class TestPipeline:
    def test_from_config(self, pipeline_config, mock_video_device):
        """"""
        pipeline = Pipeline.from_config(
            pipeline_config, mock_video_device, folder="test"
        )
        assert len(pipeline.steps) == 1
        assert isinstance(pipeline.steps[0], VideoRecorder)
        assert pipeline.steps[0].folder == "test"
