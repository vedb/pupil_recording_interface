# Test different codec speeds while reading frames from FLIR 

import pupil_recording_interface as pri
import PySpin
import h5py
import numpy as np
import time
import os
from os import listdir
from os.path import isfile, join
import cv2
from datetime import datetime
import statistics
import matplotlib.pyplot as plt
import threading
import time
n_frames = 4000

# Load images
# vid_dir = os.path.expanduser('/hdd01/kamran_sync/vedb/recordings_pilot/2019_11_12/000/')
# vid_file = os.path.join(vid_dir, 'world.mp4')
# vid = vmt.file_io.load_mp4(vid_file, frames=(0, n_frames))

#global flir_system, flir_camera, nodemap, timestamp_offset, mycapture

read_image_flag = False
# def timer_interrupt():
# 	global read_image_flag, fps
# 	next_call = time.time()
# 	while True:
# 		print('IRQ',datetime.now())
# 		next_call = next_call+1/fps;
# 		read_image_flag = True
# 		time.sleep(next_call - time.time())


def _compute_timestamp_offset(cam, number_of_iterations, camera_type):
	""" Gets timestamp offset in seconds from input camera """
	# This method is required because the timestamp stored in the camera is relative to when it was powered on, so an
	# offset needs to be applied to get it into epoch time; from tests I've done, this appears to be accurate to ~1e-3
	# seconds.

	print("Measuring TimeStamp Offset ...")
	timestamp_offsets = []
	for i in range(number_of_iterations):
		# Latch timestamp. This basically "freezes" the current camera timer into a variable that can be read with
		# TimestampLatchValue()
		cam.TimestampLatch.Execute()

		# Compute timestamp offset in seconds; note that timestamp latch value is in nanoseconds

		if(camera_type == 'BlackFly'):
			timestamp_offset = datetime.now().timestamp() - cam.TimestampLatchValue.GetValue()/1e9
		elif(camera_type == 'Chameleon'):
			timestamp_offset = datetime.now().timestamp() - cam.Timestamp.GetValue()/1e9
		else:
			print('\n\nInvalid Camera Type!!\n\n')
			return 0

	    # Append
		timestamp_offsets.append(timestamp_offset)

	# Return the median value
	return statistics.median(timestamp_offsets)


def init_FLIR(fps):
	global flir_system, flir_camera, nodemap, timestamp_offset, mycapture, camera_type
	system = PySpin.System.GetInstance()
	flir_system = system

	# Retrieve list of cameras from the system
	cam_list = system.GetCameras()
	print('List of Cameras: ', cam_list)
	num_cameras = cam_list.GetSize()

	print('Number of cameras detected: %d' % num_cameras)

	# Finish if there are no cameras
	if num_cameras == 0:
		# Clear camera list before releasing system
		cam_list.Clear()

		# Release system instance
		system.ReleaseInstance()

		raise ValueError('Not enough cameras!')

	# TODO: Clean this up! There might be multiple Cameras?!!?
	capture = cam_list[0]
	flir_camera = capture
	print('FLIR Camera : ', capture)

	# Initialize camera
	capture.Init()

	# Retrieve TL device nodemap and print device information
	nodemap_tldevice = capture.GetTLDeviceNodeMap()
	nodemap_tlstream = capture.GetTLStreamNodeMap()
	#print_device_info(nodemap_tldevice)

	capture.TriggerMode.SetValue(PySpin.TriggerMode_Off)


	# Retrieve GenICam nodemap
	nodemap = capture.GetNodeMap()

	device_model = PySpin.CStringPtr(nodemap.GetNode("DeviceModelName")).GetValue()

	if ('Chameleon' in device_model):
		camera_type = 'Chameleon'
	elif('Blackfly' in device_model):
		camera_type = 'BlackFly'
	else:
		camera_type = device_model
		print('\n\nInvalid Camera Type during initit_1!!\n\n')

	print('FLIR Camera Type = ', camera_type)
	if(camera_type == 'Chameleon'):
		print("Initializing Chameleon ...")
		node_AcquisitionFrameRateAuto = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionFrameRateAuto"))
		node_AcquisitionFrameRateAuto_off = node_AcquisitionFrameRateAuto.GetEntryByName("Off")
		node_AcquisitionFrameRateAuto.SetIntValue(node_AcquisitionFrameRateAuto_off.GetValue())


		node_AcquisitionFrameRateEnable_bool = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnabled"))
		node_AcquisitionFrameRateEnable_bool.SetValue(True) 

		node_AcquisitionFrameRate = PySpin.CFloatPtr(nodemap.GetNode("AcquisitionFrameRate"))
		node_AcquisitionFrameRate.SetValue(fps)


		if capture.ExposureAuto.GetAccessMode() != PySpin.RW:
			print("Unable to disable automatic exposure. Aborting...")
			return False

		capture.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
		print("Automatic exposure disabled...")
		if capture.ExposureTime.GetAccessMode() != PySpin.RW:
			print("Unable to set exposure time. Aborting...")
			return False

		# Ensure desired exposure time does not exceed the maximum
		exposure_time_to_set = 5000.0
		exposure_time_to_set = min(capture.ExposureTime.GetMax(), exposure_time_to_set)
		capture.ExposureTime.SetValue(exposure_time_to_set)
		print('exposure set to: ', exposure_time_to_set)


	elif(camera_type == 'BlackFly'):
		print("Initializing BlackFly ...")
		#node_AcquisitionFrameRateEnable_bool = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnable"))
		#node_AcquisitionFrameRateEnable_bool.SetValue(True) 
		capture.AcquisitionFrameRateEnable.SetValue(True)
		capture.AcquisitionFrameRate.SetValue(fps)
	else:
		print('\n\nInvalid Camera Type during initit_2!!\n\n')

	print('Set FLIR fps to:', fps)


	StreamBufferHandlingMode = PySpin.CEnumerationPtr(
		nodemap_tlstream.GetNode('StreamBufferHandlingMode'))
	StreamBufferHandlingMode_Entry = StreamBufferHandlingMode.GetEntryByName(
		'NewestOnly')
	StreamBufferHandlingMode.SetIntValue(StreamBufferHandlingMode_Entry.GetValue())
	print('Set FLIR buffer handling to: NewestOnly: ', StreamBufferHandlingMode_Entry.GetValue())

	# TODO: Find an equivalent way of reading the actual frame rate for Chameleon
	# Chameleon doesn't have this register or anything similar to this
	if (camera_type == 'BlackFly'):
		print('Actual Frame Rate = ', capture.AcquisitionResultingFrameRate.GetValue())


	timestamp_offset = _compute_timestamp_offset(capture, 20, camera_type)
	print("\nTimeStamp Offset = ", timestamp_offset/1e9)

	#  Begin acquiring images
	capture.BeginAcquisition()
	print('Acquisition Started!')
	mycapture = capture
	return capture

def _get_frame_and_timestamp(capture):

	""" Get a frame and its associated timestamp. """
	# TODO return grayscale frame if mode=='gray'
	#import PySpin
	#from datetime import datetime
	#self.previous_timestamp = self.current_timestamp
	#self.current_timestamp = time.time()
	global flir_system, flir_camera, nodemap, timestamp_offset, mycapture, camera_type
	try:
		#  Retrieve next received image
		image_result = capture.GetNextImage()


		#Ensure image completion
		if image_result.IsIncomplete():
			# TODO check if this is a valid way of handling an
			#  incomplete image
			print('\n\nImage Incomplete!')
			return _get_frame_and_timestamp(mode)

		else:
			# TODO convert to correct color format
			frame = image_result.Convert(
			    PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)


			#  Release image
			image_result.Release()
		capture.TimestampLatch.Execute()

		# TODO: Image Pointer doesn't have any GetTimeStamp() attribute
		#timestamp = float(image_result.GetTimestamp()) / 1e9
		# TODO: Temporary solution to fix the FLIR timestamp issue 	
		if(camera_type == 'BlackFly'):
			timestamp = timestamp_offset + capture.TimestampLatchValue.GetValue()/1e9
		elif(camera_type == 'Chameleon'):
			timestamp = timestamp_offset + capture.Timestamp.GetValue()/1e9
			#timestamp = capture.Timestamp.GetValue()/1e9
		else:
			print('\n\nInvalid Camera Type during get_frame!!\n\n')
		#now = datetime.now()
		#timestamp = float(datetime.timestamp(now)) / 1e9

	except PySpin.SpinnakerException as ex:
		# TODO check correct error handling
		raise ValueError(ex)
	#self.capture.EndAcquisition()
	#end = time.time()
	#print('T = ', end - start)
	# Hacking the FLIR time stamp (Kamran)
	#timestamp = time.time()
	return frame.GetNDArray(), timestamp


# on writing hdf files:
#https://stackoverflow.com/questions/43533913/optimising-hdf5-dataset-for-read-write-speed

fps = 30 
resolution = (1536, 2048)#(720, 1280)
res_y, res_x = resolution
test_dir = os.path.expanduser('~/Desktop/flir_codec_tests/FLIR_timing_tests/')
if not os.path.exists(test_dir):
	os.makedirs(test_dir)

mycapture = init_FLIR(fps)
previous_time = time.time()
previous_timestamp = time.time()
my_time_stamp = time.time()
t1 = time.time()
t2 = time.time()
# timerThread = threading.Thread(target=timer_interrupt)
# timerThread.start()

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

		for preset in ['ultrafast']:#, 'veryfast']:#, 'slow', 'veryslow']:
			for crf in ['18']:#, '18', '28', '38']:
				fname = os.path.join(test_dir, codec + '_' + preset + '_' + crf + '.hdf')
				print(f"\n\n--- Testing codec: {codec} preset: {preset} crf: {crf} ---")
				ff = pri.VideoEncoderFFMPEG(test_dir, 'ffmpeg_%s_%s_%s_%d'%(codec, preset, crf, fps), resolution, fps=fps, 
					color_format='bgr24', codec=codec, overwrite=True, preset = preset, crf = crf)

				t0 = time.time()
				#time_chk = np.zeros(n_frames)
				time_chk = np.array([], dtype = np.float32)
				#for frame in range(n_frames):
				frame = 0
				while(frame < n_frames):
				#for filename in onlyfiles[0:n_frames]:
					#print('filename:', filename)
					#im = cv2.imread(image_dir+filename)
					current_time = time.time()
					if (current_time - t1 + my_time_stamp > (1/fps)): # - (1/(.1*fps)
						#print(current_time - previous_time, 1/fps)
						t1 = time.time()
						im, my_time_stamp = _get_frame_and_timestamp(mycapture)
						#print(type(im))
						ff.write(im)
						t2 = time.time()
						
						#time_chk[frame] = t2 - t1
						#time_chk = np.append(time_chk, t2 - t1)
						time_chk = np.append(time_chk, my_time_stamp)# - previous_timestamp
						frame = frame + 1
						previous_timestamp = my_time_stamp
						previous_time = time.time()
					#else:
						#print('oops!',frame)
					#frame = frame + 1
				print('total number of frames:', frame)
				ff.video_writer.stdin.close()
				#ff.video_writer.release()
				# Save timing data
				print(f"Average frame rate for {codec}:")
				print(np.mean(1 / time_chk[2:])) # 2: to avoid startup artifacts
				print(f"Min frame rate for {codec}:")
				print(np.min(1 / time_chk[2:])) # 2: to avoid startup artifacts
				np.savez(fname.replace('.hdf','_time.npy'), time_chk)
mycapture.EndAcquisition()
print("\n\nDone!")

f = np.load(fname.replace('.hdf','_time.npy')+'.npz')['arr_0']
f = np.diff(f)
fig, axes = plt.subplots(nrows = 2, ncols = 1, figsize = (12,12))

axes[0].plot(range(len(f)),1/f, 'ob', markersize = 4)
axes[0].set_title('FPS Vs. Time', fontsize = 14)
axes[0].yaxis.grid(True)
axes[0].xaxis.grid(True)
axes[0].set_xlabel('# of frames', fontsize = 12)
axes[0].set_ylabel('FPS', fontsize = 14)


axes[1].hist(1/f, 70, facecolor = 'g', color = 'k')
axes[1].set_title('FPS histogram', fontsize = 14)
axes[1].yaxis.grid(True)
axes[1].xaxis.grid(True)
axes[1].set_xlabel('FPS', fontsize = 12)
axes[1].set_ylabel('count', fontsize = 14)

fig.suptitle('world camera fps: '+str(fps)+', CRF: '+str(crf), fontsize = 18)
plt.savefig(fname.replace('.hdf','_fps_'+str(fps)+'.png'), dpi=150)
plt.show()

