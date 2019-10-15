""""""
import os

from .odometry import OdometryInterface, OdometryRecorder
from .gaze import GazeInterface
from .video import VideoInterface, OpticalFlowInterface


def load_dataset(folder, gaze=None, odometry=None):
    """"""
    return_vals = tuple()
    if gaze is not None:
        return_vals += (
            GazeInterface(folder, source=gaze).load_dataset(),)
    if odometry is not None:
        return_vals += (
            OdometryInterface(folder, source=odometry).load_dataset(),)

    if len(return_vals) == 1:
        return_vals = return_vals[0]

    return return_vals


def write_netcdf(folder, output_folder=None, gaze=None, odometry=None):
    """"""
    if gaze is not None:
        if output_folder is not None:
            filename = os.path.join(output_folder, 'gaze.nc')
        else:
            filename = None
        GazeInterface(
            folder, source=gaze).write_netcdf(filename=filename)
    if odometry is not None:
        if output_folder is not None:
            filename = os.path.join(output_folder, 'odometry.nc')
        else:
            filename = None
        OdometryInterface(
            folder, source=odometry).write_netcdf(filename=filename)
