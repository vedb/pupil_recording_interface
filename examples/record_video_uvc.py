from pupil_recording_interface.recorder.video import \
    VideoConfig, VideoRecorder

if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/test'

    # aliases for video devices (you might need to change the values)
    aliases = {
        'eye0': 'Pupil Cam1 ID0',
        'eye1': 'Pupil Cam1 ID1',
        'world': 'Pupil Cam1 ID2',
    }

    # camera configurations
    configs = [
        VideoConfig(
            'uvc', device_name='world', resolution=(1280, 720), fps=60),
        VideoConfig(
            'uvc', device_name='eye0', resolution=(320, 240), fps=120,
            color_format='gray'),
        VideoConfig(
            'uvc', device_name='eye1', resolution=(320, 240), fps=120,
            color_format='gray'),
    ]

    # start recorder
    recorder = VideoRecorder(folder, configs, aliases, show_video=True)
    recorder.run()
