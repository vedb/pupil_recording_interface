from pupil_recording_interface.config import VideoConfig
from pupil_recording_interface.calibration import MultiCameraCalibration

if __name__ == '__main__':

    # recording folder
    folder = '~/recordings/calibration_test'

    # stream configurations
    configs = [
        VideoConfig(
            'uvc', 'Pupil Cam1 ID2', name='world',
            resolution=(1280, 720), fps=30, color_format='gray'),
        VideoConfig(
            't265', 't265',
            resolution=(1696, 800), fps=30, color_format='gray'),
    ]

    # calibrate
    calibration = MultiCameraCalibration(folder, configs, policy='overwrite')
    calibration.run()
