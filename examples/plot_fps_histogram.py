import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


df = pd.read_csv('/home/veddy/Code/pupil_recording_interface/examples/30fps_fullRes_.csv')

fig = plt.figure(figsize = (10,8))
ax = df[['eye0', 'eye1', 'world', 't265', 'odometry']].plot.hist(bins = 150, alpha = 0.4)
plt.show()