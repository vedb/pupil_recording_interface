from pupil_recording_interface import (
    VideoConfig,
    VideoRecorder,
    MultiStreamRecorder,
)
from pupil_recording_interface.config import OdometryConfig

if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/flir_test"

    # Todo: Change this according to pupils instructions
    # string that uniquely identifies the FLIR camera
    flir_uid = "FLIR_19238305"

    codec = "libx265"
    # camera configurations
    recording_duration = 60
    flir_fps = 30
    # flir_resolution = (1536, 2048)#(1024, 1280)#
    # flir_resolution = (768, 1024)
    flir_resolution = (1024, 1280)
    # 100 fps : 9900.0 #50 fps : 19000 # 30 fps : 31000.0
    exposure_value = 31000.0
    gain = 18
    configs = [
        VideoConfig(
            "flir",
            flir_uid,
            name="world",
            codec=codec,
            resolution=flir_resolution,
            fps=flir_fps,
            exposure_value=exposure_value,
            gain=gain,
        ),  # (1536, 2048)
        VideoConfig(
            "uvc",
            "Pupil Cam2 ID0",
            name="eye0",
            codec=codec,
            resolution=(400, 400),
            fps=120,
            color_format="gray",
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam2 ID1",
            name="eye1",
            codec=codec,
            resolution=(400, 400),
            fps=120,
            color_format="gray",
        ),
        VideoConfig(
            "t265", "t265", resolution=(800, 1696), fps=30, color_format="gray"
        ),
        OdometryConfig("t265", "t265", name="odometry"),
    ]

    # change this to False for multi-threaded recording
    single_threaded = False

    if single_threaded:
        recorder = VideoRecorder.from_config(
            configs[0], folder, overwrite=True
        )
        recorder.show_video = False
    else:
        recorder = MultiStreamRecorder(
            folder, configs, show_video=False, duration=recording_duration
        )
    recorder.run()
