from pupil_recording_interface.recorder.realsense import VideoCaptureT265

if __name__ == '__main__':

    # recording folder
    folder = '.'

    # start recorder
    recorder = VideoCaptureT265(
        folder, device_name='t265', resolution=(800, 848), fps=30,
        color_format='gray', show_video=True, overwrite=True)
    recorder.run()
