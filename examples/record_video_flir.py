from pupil_recording_interface import \
    VideoConfig, VideoRecorder, MultiStreamRecorder
from pupil_recording_interface.config import OdometryConfig
if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/flir_test'

    #Todo: Change this according to pupils instructions
    # string that uniquely identifies the FLIR camera
    flir_uid = 'FLIR_19238305'
    #flir_uid = 'CHANGEME'

    codec = 'libx265'
    # camera configurations
    configs = [
        VideoConfig(
            'flir', flir_uid, name='world', codec = codec,
            resolution=(1536, 2048), fps=50),
        VideoConfig(
            'uvc', 'Pupil Cam2 ID0', name='eye0', codec = codec,
            resolution=(400, 400), fps=120, color_format='gray'),
         VideoConfig(
            'uvc', 'Pupil Cam2 ID1', name='eye1', codec = codec,
            resolution=(400, 400), fps=120, color_format='gray'),
        VideoConfig(
            't265', 't265',
            resolution=(800, 1696), fps=30, color_format='gray'),
        OdometryConfig(
            't265', 't265', name='odometry'),
    ]

    # change this to False for multi-threaded recording
    single_threaded = False

    if single_threaded:
        recorder = VideoRecorder.from_config(
            configs[0], folder, overwrite=True)
        recorder.show_video = False
    else:
        recorder = MultiStreamRecorder(folder, configs, show_video=False, duration = 30)
    #while recorder.all_devices_initialized is False:
    #    pass

    recorder.run()
