# Test different codec speeds. 

import pupil_recording_interface as pri
import vm_tools as vmt
import h5py
import numpy as np
import time
import os

n_frames = 100

# Load images
vid_dir = os.path.expanduser('~/pomsync/vedb/recordings_pilot/2019_11_12/000/')
vid_file = os.path.join(vid_dir, 'world.mp4')
vid = vmt.file_io.load_mp4(vid_file, frames=(0, n_frames))

# on writing hdf files:
#https://stackoverflow.com/questions/43533913/optimising-hdf5-dataset-for-read-write-speed

fps = 55 # Unclear if this borkles things
resolution = (720, 1280)
res_y, res_x = resolution
test_dir ='/data/flir_dump/'

# Note on codecs: https://lists.ffmpeg.org/pipermail/ffmpeg-user/2015-January/024838.html
# THIS ONE IS REALLY GOOD:
# https://superuser.com/questions/486325/lossless-universal-video-format
# Note options for ffmpeg h264 & h265 for lossless, fast, slow compression
for codec in ['hdf', 'hdf_compressed4', 'rawvideo', 'libx264', 'libx265']:
	print(f"--- Testing {codec} ---")
	fname = os.path.join(test_dir, codec + '.hdf')
	if 'hdf' in codec:
		hf = h5py.File(fname, mode='w')
		hfargs = dict(shape=(res_y, res_x, 3, n_frames), dtype=np.uint8)
		if codec != 'hdf':
			# Want compressed hdf
			# Compression value can be 0-9, default is 4, worth varying this
			cval = int(codec[-1])
			hfargs.update(compression='gzip', compression_opts=cval)
		hf.create_dataset('video', **hfargs)
	else:
		ff = pri.VideoEncoderFFMPEG(test_dir, 'ffmpeg_%s_%d'%(codec, fps), resolution, 
			overwrite=True, color_format='bgr24', codec=codec, fps=fps, )

	t0 = time.time()
	time_chk = np.zeros(n_frames)
	for frame in range(n_frames):
		t1 = time.time()
		if 'hdf' in codec:
			hf['video'][..., frame] = vid[..., frame]
		else:
			ff.write(vid[..., ::-1, frame])
		t2 = time.time()
		time_chk[frame] = t2 - t1
	if 'hdf' in codec:
		hf.close()
	# Save timing data
	print(f"Average frame rate for {codec}:")
	print(np.mean(1 / time_chk[2:])) # 2: to avoid startup artifacts
	print(f"Min frame rate for {codec}:")
	print(np.min(1 / time_chk[2:])) # 2: to avoid startup artifacts
	np.savez(fname.replace('.hdf','_time.npy'), time_chk)
