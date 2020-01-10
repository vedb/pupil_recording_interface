import os

import numpy as np

from pupil_recording_interface.recorder.video import \
    VideoConfig, VideoRecorder

if __name__ == '__main__':

    # set recording folder
    folder = '~/recordings/test'

    # set up camera configurations
    configs = [
        VideoConfig(device_name='world', resolution=(1280, 720), fps=30),
        VideoConfig(device_name='eye0', resolution=(320, 240), fps=120),
        VideoConfig(device_name='eye1', resolution=(320, 240), fps=120),
    ]

    # start recorder
    recorder = VideoRecorder(folder, configs, show_video=True)
    recorder.run()

    # check recorded frame rates
    print('Recorded frame rates:')
    for f in os.listdir(recorder.folder):
        if f.endswith('_timestamps.npy'):
            timestamps = np.load(os.path.join(recorder.folder, f))
            print('* {}: {:.3f} Hz'.format(f, np.mean(1./np.diff(timestamps))))
