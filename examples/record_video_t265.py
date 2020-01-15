from pupil_recording_interface.recorder.video import VideoRecorder, VideoConfig

if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/test'

    # camera configurations
    configs = [
        VideoConfig(
            't265', device_name='t265', resolution=(800, 848), fps=30,
            color_format='gray'),
    ]

    # start recorder
    recorder = VideoRecorder(folder, configs, None, show_video=True)
    recorder.run()
