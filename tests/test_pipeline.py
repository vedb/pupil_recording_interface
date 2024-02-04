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
        assert str(pipeline.steps[0].folder) == "test"

    def test_set_context(self, video_stream):
        """"""
        pipeline = Pipeline([VideoRecorder("test", (1280, 720), 30)])
        pipeline.set_context(video_stream)

        assert pipeline.context is video_stream
        for step in pipeline.steps:
            assert step.context is video_stream
