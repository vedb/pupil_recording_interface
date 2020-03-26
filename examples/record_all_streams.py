from pupil_recording_interface.config import VideoConfig, OdometryConfig
from pupil_recording_interface import MultiStreamRecorder

if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # stream configurations
    configs = [
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=60,
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
        ),
        VideoConfig(
            "t265", "t265", resolution=(1696, 800), fps=30, color_format="gray"
        ),
        OdometryConfig("t265", "t265", name="odometry"),
    ]

    recorder = MultiStreamRecorder(
        folder, configs, policy="overwrite", show_video=True
    )

    recorder.run()
