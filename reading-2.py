import pupil_recording_interface as pri
gaze = pri.load_dataset(pri.get_test_recording(), gaze='2d Gaze Mapper ')
reader = pri.VideoReader(
    pri.get_test_recording(), norm_pos=gaze.gaze_norm_pos, roi_size=64
)
frame = reader.load_frame(100)

import matplotlib.pyplot as plt
fig = plt.figure(figsize=(3.2, 3.2))
ax = plt.axes([0,0,1,1], frameon=False)
ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)
ax.imshow(frame[:, :, ::-1])