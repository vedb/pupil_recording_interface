import numpy as np
import os
from os import listdir
from os.path import isfile, join
import matplotlib.pyplot as plt


# Change me if you only wanna plot the video file sizes
# Else the code will plot the frame rates
plot_the_file_size = False

if plot_the_file_size == True:
	y_label = '# Bytes'
	super_title = "# of Bytes Vs. Different Codec Options"

else:
	y_label = 'FPS'
	super_title = "FPS Vs. Different Codec Options (Capture + Encoding)"
result_dir = os.path.expanduser('~/Desktop/flir_codec_tests/third_good_results/all/')
print('result directory:\n', result_dir)
npzfiles = [f for f in listdir(result_dir) if isfile(join(result_dir, f)) and join(result_dir, f).endswith(".npz")]


#for filename in npzfiles: print(filename)

print("\n\n file name:")
codecs = []
presets = []
crfs = []
data = dict(dtype = np.array)
file_size = dict(dtype = np.array)
for filename in npzfiles: 
	file_string = os.path.splitext(os.path.splitext(os.path.basename(filename))[0])[0].split('_')
	codecs.append(file_string[0])
	presets.append(file_string[1])
	crfs.append(file_string[2])

	if(plot_the_file_size == False):
		data[file_string[0], file_string[1], file_string[2]] = 1/np.load(result_dir + filename)['arr_0']
	else:
		fname = result_dir+'ffmpeg_'+filename
		fname = fname.replace('time.npy.npz', '60.mp4')
		#print(fname, float(os.path.getsize(fname)))
		data[file_string[0], file_string[1], file_string[2]] = np.zeros(100)+float(os.path.getsize(fname))



number_of_codecs = len(np.unique(codecs))
number_of_presets = len(np.unique(presets))
number_of_crfs = len(np.unique(crfs))


print('number of presets and crfs:',number_of_codecs, number_of_presets, number_of_crfs)
#print('data = ', data)

presets_sorted = ['ultrafast', 'veryfast']#, 'slow', 'veryslow']

fig, axes = plt.subplots(nrows = 1, ncols = number_of_crfs, sharey = True, figsize = (12,8))

all_data = [data[np.unique(codecs)[0], p, np.unique(crfs)[0]] for p in presets_sorted]
labels = [p for p in presets_sorted]

# rectangular box plot
bplot1 = axes[0].boxplot(all_data,
						notch=True,
						vert=True,  # vertical box alignment
						patch_artist=True,  # fill with color
						labels=labels,  # will be used to label x-ticks
						showfliers = False)
axes[0].set_title('CRF: '+np.unique(crfs)[0], fontsize = 14)

all_data = [data[np.unique(codecs)[0], p, np.unique(crfs)[1]] for p in presets_sorted]
labels = [p for p in presets_sorted]

# notch shape box plot
bplot2 = axes[1].boxplot(all_data,
						notch=True,  # notch shape
						vert=True,  # vertical box alignment
						patch_artist=True,  # fill with color
						labels=labels,  # will be used to label x-ticks
						showfliers = False)
axes[1].set_title('CRF: '+np.unique(crfs)[1], fontsize = 14)


all_data = [data[np.unique(codecs)[0], p, np.unique(crfs)[2]] for p in presets_sorted]
labels = [p for p in presets_sorted]

# notch shape box plot
bplot3 = axes[2].boxplot(all_data,
						notch=True,  # notch shape
						vert=True,  # vertical box alignment
						patch_artist=True,  # fill with color
						labels=labels,  # will be used to label x-ticks
						showfliers = False)
axes[2].set_title('CRF: '+np.unique(crfs)[2], fontsize = 14)


all_data = [data[np.unique(codecs)[0], p, np.unique(crfs)[3]] for p in presets_sorted]
labels = [p for p in presets_sorted]

# notch shape box plot
bplot4 = axes[3].boxplot(all_data,
						notch=True,  # notch shape
						vert=True,  # vertical box alignment
						patch_artist=True,  # fill with color
						labels=labels,  # will be used to label x-ticks
						showfliers = False)
axes[3].set_title('CRF: '+np.unique(crfs)[3], fontsize = 14)

# fill with colors
colors = ['pink', 'lightblue', 'lightgreen', 'green']
for bplot in (bplot1, bplot2, bplot3, bplot4):
    for patch, color in zip(bplot['boxes'], colors):
        patch.set_facecolor(color)

# adding horizontal grid lines
for ax in axes:
    ax.yaxis.grid(True)
    ax.set_xlabel('preset', fontsize = 14)
    ax.set_ylabel(y_label, fontsize = 14)

fig.suptitle(super_title, fontsize = 18)
#fig.suptitle("Video size for 500 Images", fontsize = 18)
plt.show()



# for codec in codecs:
# 	plt.subplot(number_of_codecs,1,codecs.index(codec))
# 	for p in presets:
# 		myData = [data[codec, p, crf]] for crf in  
# 		plt.boxplot(myData, )



#print("\n\n Reading ...")
# for filename in npzfiles: 
# 	print(filename)
# 	results = np.load(result_dir + filename)
# 	print(results, type(results))

