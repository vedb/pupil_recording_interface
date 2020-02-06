# Test different codec speeds. 

import pupil_recording_interface as pri
#import vm_tools as vmt
import h5py
import numpy as np
import time
import os
from os import listdir
from os.path import isfile, join
import cv2

n_frames = 500

# Load images
# vid_dir = os.path.expanduser('/hdd01/kamran_sync/vedb/recordings_pilot/2019_11_12/000/')
# vid_file = os.path.join(vid_dir, 'world.mp4')
# vid = vmt.file_io.load_mp4(vid_file, frames=(0, n_frames))


image_dir = '/home/veddy/Videos/FLIR_images/capture_2/png_60fps/'
image_dir = os.path.expanduser('/home/veddy/Videos/FLIR_images/capture_2/png_60fps/')
onlyfiles = [f for f in listdir(image_dir) if isfile(join(image_dir, f))]
# sort the images since the temporal correlation of the images affects the compression
onlyfiles.sort(key=lambda x: os.path.getmtime(image_dir + x))

print('--- Reading images')
vid = []
for filename in onlyfiles[0:n_frames]:
	#print('filename:', filename)
	im = cv2.imread(image_dir+filename)
	#print('image frame size: ', im.shape)
	vid.append(im)#[0:1280, 0:720,:]
	#vid = np.append([vid], [np.array(im)], axis = 2)
vid = np.array(vid)
print('video shape (before)', vid.shape)
vid = vid.transpose(1,2,3,0)
print('video shape', vid.shape)


# on writing hdf files:
#https://stackoverflow.com/questions/43533913/optimising-hdf5-dataset-for-read-write-speed

fps = 60 # Unclear if this borkles things
resolution = (1536, 2048)#(720, 1280)
#resolution = (2048, 1536)
res_y, res_x = resolution
test_dir = os.path.expanduser('~/Desktop/flir_codec_tests/')
if not os.path.exists(test_dir):
	os.makedirs(test_dir)

# Note on codecs: https://lists.ffmpeg.org/pipermail/ffmpeg-user/2015-January/024838.html
# THIS ONE IS REALLY GOOD:
# https://superuser.com/questions/486325/lossless-universal-video-format
# Note options for ffmpeg h264 & h265 for lossless, fast, slow compression
for codec in ['libx264']:#'rawvideo', 'libx265', 'rawvideo']:#, 'hdf']:#, 'hdf_compressed4']:
	
	fname = os.path.join(test_dir, codec + '.hdf')
	if 'hdf' in codec:
		print(f"\n\n--- Testing codec: {codec} ---")
		hf = h5py.File(fname, mode='w')
		hfargs = dict(shape=(res_x, res_y, 3, n_frames), dtype=np.uint8)
		if codec != 'hdf':
			# Want compressed hdf
			# Compression value can be 0-9, default is 4, worth varying this
			cval = int(codec[-1])
			hfargs.update(compression='gzip', compression_opts=cval)

		hf.create_dataset('video', **hfargs)
	
		t0 = time.time()
		time_chk = np.zeros(n_frames)
		for frame in range(n_frames):
			t1 = time.time()
			hf['video'][..., frame] = vid[..., frame]
			t2 = time.time()
			time_chk[frame] = t2 - t1
		hf.close()
		# Save timing data
		print(f"Average frame rate for {codec}:")
		print(np.mean(1 / time_chk[2:])) # 2: to avoid startup artifacts
		print(f"Min frame rate for {codec}:")
		print(np.min(1 / time_chk[2:])) # 2: to avoid startup artifacts
		np.savez(fname.replace('.hdf','_time.npy'), time_chk)

	elif codec == 'rawvideo':
		preset = 'None'
		crf = 'None'
		fname = os.path.join(test_dir, codec + '_' + preset + '_' + crf + '.hdf')
		print(f"\n\n--- Testing codec: {codec} preset: {preset} crf: {crf} ---")
		ff = pri.VideoEncoderFFMPEG(test_dir, 'ffmpeg_%s_%s_%s_%d'%(codec, preset, crf, fps), resolution, fps=fps, 
			color_format='bgr24', codec=codec, overwrite=True, preset = preset, crf = crf)

		t0 = time.time()
		time_chk = np.zeros(n_frames)
		#for frame in range(n_frames):
		frame = 0
		for filename in onlyfiles[0:n_frames]:
			#print('filename:', filename)
			im = cv2.imread(image_dir+filename)

			t1 = time.time()
			#ff.write(vid[..., frame])
			ff.write(im)
			t2 = time.time()
			time_chk[frame] = t2 - t1
			frame = frame + 1

		ff.video_writer.stdin.close()	
		#ff.video_writer.release()
		# Save timing data
		print(f"Average frame rate for {codec}:")
		print(np.mean(1 / time_chk[2:])) # 2: to avoid startup artifacts
		print(f"Min frame rate for {codec}:")
		print(np.min(1 / time_chk[2:])) # 2: to avoid startup artifacts
		np.savez(fname.replace('.hdf','_time.npy'), time_chk)		
	else:

		for preset in ['ultrafast', 'veryfast', 'slow', 'veryslow']:
			for crf in ['0', '18', '28', '38']:
				fname = os.path.join(test_dir, codec + '_' + preset + '_' + crf + '.hdf')
				print(f"\n\n--- Testing codec: {codec} preset: {preset} crf: {crf} ---")
				ff = pri.VideoEncoderFFMPEG(test_dir, 'ffmpeg_%s_%s_%s_%d'%(codec, preset, crf, fps), resolution, fps=fps, 
					color_format='bgr24', codec=codec, overwrite=True, preset = preset, crf = crf)

				t0 = time.time()
				time_chk = np.zeros(n_frames)
				for frame in range(n_frames):
				#frame = 0
				#for filename in onlyfiles[0:n_frames]:
					#print('filename:', filename)
					#im = cv2.imread(image_dir+filename)

					t1 = time.time()
					ff.write(vid[..., frame])
					#ff.write(im)
					t2 = time.time()
					time_chk[frame] = t2 - t1
					#frame = frame + 1

				ff.video_writer.stdin.close()	
				#ff.video_writer.release()
				# Save timing data
				print(f"Average frame rate for {codec}:")
				print(np.mean(1 / time_chk[2:])) # 2: to avoid startup artifacts
				print(f"Min frame rate for {codec}:")
				print(np.min(1 / time_chk[2:])) # 2: to avoid startup artifacts
				np.savez(fname.replace('.hdf','_time.npy'), time_chk)
				

