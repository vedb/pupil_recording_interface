import sys, os
sys.path.append('/home/veddy/Code/pupil_recording_interface/')

from pupil_recording_interface.recorder.video import \
    VideoConfig, VideoRecorder

if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/test'

    # aliases for video devices (you might need to change the values)
    aliases = {
        'eye0': 'Pupil Cam2 ID0',
        'eye1': 'Pupil Cam2 ID1',
        'world': 'TODO',
    }

    # camera configurations
    configs = [
        VideoConfig(
            'flir', device_name='world', resolution=(2048, 1536), fps=60),
        VideoConfig(
            'uvc', device_name='eye0', resolution=(400, 400), fps=120,
            color_format='gray'),
        VideoConfig(
            'uvc', device_name='eye1', resolution=(400, 400), fps=120,
            color_format='gray'),
    ]

    # start recorder
    recorder = VideoRecorder(folder, configs, aliases, show_video=True)
    recorder.run()
