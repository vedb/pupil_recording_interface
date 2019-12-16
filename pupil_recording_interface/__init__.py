""""""
import os

from .base import BaseInterface
from .odometry import OdometryInterface, OdometryRecorder
from .gaze import GazeInterface
from .video import VideoInterface, OpticalFlowInterface


__all__ = [
    'load_dataset',
    'load_info',
    'load_user_info',
    'write_netcdf',
    'GazeInterface',
    'OdometryInterface',
    'VideoInterface',
    'OpticalFlowInterface',
    'OdometryRecorder'
]


def load_dataset(folder, gaze=None, odometry=None):
    """ Load a recording as an xarray.Dataset.

    Parameters
    ----------
    folder
    gaze
    odometry

    Returns
    -------

    """
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
    """ Export a recording in the netCDF format.

    Parameters
    ----------
    folder
    output_folder
    gaze
    odometry

    Returns
    -------

    """
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


def load_info(folder):
    """ Load recording info.

    Parameters
    ----------
    folder

    Returns
    -------

    """
    return BaseInterface(folder).info


def load_user_info(folder):
    """ Load user info.

    Parameters
    ----------
    folder

    Returns
    -------

    """
    return BaseInterface(folder).user_info
