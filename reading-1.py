import pupil_recording_interface as pri
reader = pri.VideoReader(pri.get_test_recording())
frame = reader.load_raw_frame(100)

import matplotlib.pyplot as plt
fig = plt.figure(figsize=(12.8, 7.2))
ax = plt.axes([0,0,1,1], frameon=False)
ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)
ax.imshow(frame[:, :, ::-1])