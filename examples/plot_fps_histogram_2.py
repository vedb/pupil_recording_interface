import numpy as np
import matplotlib.pyplot as plt

f = np.load("/home/veddy/recordings/flir_test/326/world_timestamps.npy")
f = np.diff(f)
fig, axes = plt.subplots(nrows = 2, ncols = 1, figsize = (12,12))

axes[0].plot(range(len(f)),1/f, 'ob', markersize = 4, alpha = 0.4)
axes[0].set_title('FPS Vs. Time', fontsize = 14)
axes[0].yaxis.grid(True)
axes[0].xaxis.grid(True)
axes[0].set_xlabel('# of frames', fontsize = 12)
axes[0].set_ylabel('FPS', fontsize = 14)


axes[1].hist(1/f, 100, facecolor = 'g', edgecolor = 'k', linewidth = 1)
axes[1].set_title('FPS histogram', fontsize = 14)
axes[1].yaxis.grid(True)
axes[1].xaxis.grid(True)
axes[1].set_xlabel('FPS', fontsize = 12)
axes[1].set_ylabel('count', fontsize = 14)

fig.suptitle('world camera', fontsize = 18)
#plt.savefig(fname.replace('.hdf','_fps_'+str(fps)+'.png'), dpi=150)
plt.show()
