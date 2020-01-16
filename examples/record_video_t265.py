from pupil_recording_interface.config import VideoConfig, OdometryConfig
from pupil_recording_interface import MultiStreamRecorder

if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/test'

    # stream configurations
    configs = [
        VideoConfig(
            't265', 't265',
            resolution=(1696, 800), fps=30, color_format='gray'),
        OdometryConfig(
            't265', 't265', name='odometry'),
    ]

    # start recorder
    recorder = MultiStreamRecorder(folder, configs, show_video=True)
    recorder.run()
