from pupil_recording_interface.recorder.video import \
    VideoConfig, VideoRecorder

if __name__ == '__main__':

    # set recording folder
    folder = '~/recordings/test'

    # set up camera configurations
    configs = [
        VideoConfig(device_name='world', resolution=(1280, 720), fps=60),
        VideoConfig(device_name='eye0', resolution=(320, 240), fps=120,
                    color_format='gray'),
        VideoConfig(device_name='eye1', resolution=(320, 240), fps=120,
                    color_format='gray'),
    ]

    # start recorder
    recorder = VideoRecorder(folder, configs, show_video=True)
    recorder.run()
