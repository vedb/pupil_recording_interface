""""""
import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface.reader import BaseReader
from pupil_recording_interface.externals.file_methods import load_object


class MarkerReader(BaseReader):
    """ Reader for reference marker data. """

    @property
    def export_name(self):
        """ Name of exported files. """
        return "reference_locations"

    @staticmethod
    def _load_markers(folder, topic="reference_locations"):
        """ Load reference marker data from a .msgpack file. """
        markers = load_object(folder / f"{topic}.msgpack")["data"]

        df = pd.DataFrame(
            markers, columns=["img_pos", "frame_index", "timestamp"]
        )

        return MarkerReader._extract_marker_data(df)

    @staticmethod
    def _extract_marker_data(df):
        """"""
        data = {
            "location": np.array(df.img_pos.to_list()),
            "frame_index": df.frame_index,
            "timestamp": df.timestamp,
        }

        return data

    @staticmethod
    def _create_dataset(data, info):
        """ Create an xarray.Dataset from reference marker data. """
        t = BaseReader._timestamps_to_datetimeindex(data["timestamp"], info)

        coords = {
            "time": t.values,
            "pixel_axis": ["x", "y"],
        }

        data_vars = {
            "frame_index": ("time", data["frame_index"]),
            "location": (["time", "pixel_axis"], data["location"]),
        }

        ds = xr.Dataset(data_vars, coords)

        # sort and remove duplicate samples
        ds.sortby("time")
        _, index = np.unique(ds["time"], return_index=True)
        ds = ds.isel(time=index)

        return ds

    @staticmethod
    def _dataset_from_list(marker_list, info):
        """ Create dataset from list of dicts. """
        df = pd.DataFrame(marker_list)
        data = MarkerReader._extract_marker_data(df)
        ds = MarkerReader._create_dataset(data, info)

        return ds

    def load_dataset(self):
        """ Load pupil data as an xarray Dataset.

        Returns
        -------
        xarray.Dataset
            The pupil data as a dataset.
        """
        data = self._load_markers(self.folder / "offline_data")

        return self._create_dataset(data, self.info)
