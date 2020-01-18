from pupil_recording_interface import \
    VideoConfig, VideoRecorder, MultiStreamRecorder

if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/flir_test'

    # string that uniquely identifies the FLIR camera
    flir_uid = 'FLIR ID_None'
    #flir_uid = 'CHANGEME'

    # camera configurations
    configs = [
        VideoConfig(
            'flir', flir_uid, name='world',
            resolution=(2048, 1536), fps=30),
        VideoConfig(
            'uvc', 'Pupil Cam2 ID0', name='eye0',
            resolution=(400, 400), fps=30, color_format='gray'),
        VideoConfig(
            'uvc', 'Pupil Cam2 ID1', name='eye1',
            resolution=(400, 400), fps=30, color_format='gray'),
    ]

    # change this to False for multi-threaded recording
    single_threaded = False

    if single_threaded:
        recorder = VideoRecorder.from_config(
            configs[0], folder, overwrite=True)
        recorder.show_video = True
    else:
        recorder = MultiStreamRecorder(folder, configs, show_video=True)

    recorder.run()
