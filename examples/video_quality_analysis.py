# Video Quality analysis
# The goal of this script is to compare the quality of videos generated using
# different Codec parameters via a few well-known metrics such as:
# 	VIF (sometimes called VIF-P or VIFP), Visual Information Fidelity
#	SSIM, Structural Similarity Metric
#	PSNR, Peak Signal to Noise Ratio
#	RECO, Relative Polar Edge Coherence
#	NIQE, Natural Image Quality Evaluator
import numpy as np
import os
from os import listdir
from os.path import isfile, join
import vm_tools as vmt

import sys
import os.path
import pickle
import sewar

mydirectory = "/home/kamran/Code/pupil_recording_interface/examples/video-quality-master/"
sys.path.append(mydirectory)

#for directory in sys.path:
#    print(directory)

import matplotlib.pyplot as plt


# Change me if you only wanna plot the video file sizes
# Else the code will plot the frame rates
super_title = "FPS Vs. Different Codec Options (Desktop:FLIR Capture)"

result_dir = os.path.expanduser('/hdd01/kamran_sync/vedb/ved_data_testing/flir_codec_tests/tests_on_XPS/analysis_results_chunk/')
print('result directory:\n', result_dir)
mp4files = [f for f in listdir(result_dir) if isfile(join(result_dir, f)) and join(result_dir, f).endswith(".mp4")]

ref_video_files = []
comp_video_files = []
for filename in mp4files:
	if '_0' in filename:
		ref_video_files.append(filename)
	else:
		comp_video_files.append(filename)

print('# of reference videos:',len(ref_video_files))
print('# of compressed videos:',len(comp_video_files))

n_frames = 5
print("running analysis for %d frames"%(n_frames))

codecs = []
presets = []
crfs = ['18', '28', '38']
data = dict()
file_size = dict()
video_files = []

metric_list = ['mse', 'rmse', 'psnr', 'ssim','uqi', 'scc', 'vifp'] #'niqe'


for filename in comp_video_files: 
	file_string = os.path.splitext(os.path.splitext(os.path.basename(filename))[0])[0].split('_')
	print(file_string)
	#presets.append(file_string[2])
	#crfs.append(file_string[3])
	preset = file_string[2]
	crf = file_string[3]

	fname = result_dir+filename
	#video_files.append(fname)
	print(filename, ':', float(os.path.getsize(fname)), ' MB')
	print('reading reference video ...')
	vid_1 = np.array(vmt.file_io.load_mp4(fname, frames=(0, n_frames)))
	print(vid_1.shape)

	fname_ref = fname.replace(crf, '0')
	print(filename.replace(crf, '0'), ':', float(os.path.getsize(fname_ref)), ' MB')

	print('reading compressed video ...')
	vid_0 = np.array(vmt.file_io.load_mp4(fname_ref, frames=(0, n_frames)))
	print(vid_0.shape)

	mse_values = []
	rmse_values = []
	uqi_values = []
	scc_values = []
	rase_values = []
	sam_values = []

	vifp_values = []


	for frame_number in range(n_frames):
		print('\rframe_number = '+str(frame_number), end='')

		#for color in range(color_channels):
		frame_0 = np.array(vid_0[:,:,:,frame_number], dtype = np.float32)
		#print(frame_0.shape)
		frame_1 = np.array(vid_1[:,:,:,frame_number], dtype = np.float32)
		#print(frame_1.shape)

		mse_values.append(sewar.mse(frame_0, frame_1))
		rmse_values.append(sewar.rmse(frame_0, frame_1))
		uqi_values.append(sewar.uqi(frame_0, frame_1))
		#scc_values.append(sewar.scc(frame_0, frame_1))
		rase_values.append(sewar.rase(frame_0, frame_1))
		sam_values.append(sewar.sam(frame_0, frame_1))

	data[file_string[2], file_string[3], 'mse'] = np.asarray(mse_values, dtype = np.float32)
	data[file_string[2], file_string[3], 'rmse'] = np.asarray(rmse_values, dtype = np.float32)
	data[file_string[2], file_string[3], 'uqi'] = np.asarray(uqi_values, dtype = np.float32)
	#data[file_string[2], file_string[3], 'scc'] = np.asarray(scc_values, dtype = np.float32)
	data[file_string[2], file_string[3], 'rase'] = np.asarray(rase_values, dtype = np.float32)
	data[file_string[2], file_string[3], 'sam'] = np.asarray(sam_values, dtype = np.float32)
	print('\n\n')


for a in data.keys():
	print(a, data[a].shape)

#np.save(result_dir+'video_quality_analysis',data)

pickle_out = open(result_dir+'video_quality_analysis.pickle',"wb")
pickle.dump(data, pickle_out)
pickle_out.close()


pickle_in = open(result_dir+'video_quality_analysis.pickle',"rb")
example_dict = pickle.load(pickle_in)

print('reading saved pickle')
for a in example_dict.keys():#, data.items()):
	print(a, example_dict[a].shape, example_dict[a].mean(), example_dict[a].max())
