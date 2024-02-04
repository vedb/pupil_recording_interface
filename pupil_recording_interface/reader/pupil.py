""""""
import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface.reader import BaseReader


class PupilReader(BaseReader):
    """ Reader for pupil data. """

    def __init__(self, folder, source="recording", method="pye3d"):
        """ Constructor.

        Parameters
        ----------
        folder : str or pathlib.Path
            Path to the recording folder.

        source : str or dict, default 'recording'
            The source of the data. If 'recording', the recorded data will
            be used.

        method : str, default "pye3d"

        """
        super().__init__(folder)

        self.source = source
        self.method = method

    @property
    def export_name(self):
        """ Name of exported files. """
        return "pupil"

    @staticmethod
    def _load_pupil(folder, method, topic="pupil"):
        """ Load pupil data from a .pldata file. """
        df = BaseReader._load_pldata_as_dataframe(folder, topic)

        # reduce data to requested method
        if method not in ("2d", "3d", "pye3d"):
            raise ValueError(f"Unsupported method: {method}")

        df = df[df.method.str.startswith(method)]

        if df.size == 0:
            raise ValueError(
                f"No pupil data in {folder / (topic + '.pldata')} "
                f"from method {method}"
            )

        return PupilReader._extract_pupil_data(df, method)

    @staticmethod
    def _extract_pupil_data(df, method):
        """ Extract pupil data from a DataFrame. """
        ellipse = pd.DataFrame(df.ellipse.to_list())

        data = {
            "timestamp": df.timestamp,
            "confidence": df.confidence,
            "norm_pos": np.array(df.norm_pos.to_list()),
            "diameter": df.diameter,
            "eye": df.id,
            "ellipse_center": np.array(ellipse.center.to_list()),
            "ellipse_axes": np.array(ellipse["axes"].to_list()),
            "ellipse_angle": ellipse.angle,
        }

        if method in ("3d", "pye3d"):
            for column in [
                "diameter_3d",
                "theta",
                "phi",
                "model_confidence",
            ]:
                data[column] = df[column]

            circle_3d = pd.DataFrame(df.circle_3d.to_list())
            data["circle_center"] = np.array(circle_3d.center.to_list())
            data["circle_normal"] = np.array(circle_3d.normal.to_list())
            data["circle_radius"] = circle_3d.radius

            sphere = pd.DataFrame(df.sphere.to_list())
            data["sphere_center"] = np.array(sphere.center.to_list())
            data["sphere_radius"] = sphere.radius

            projected_sphere = pd.DataFrame(df.projected_sphere.to_list())
            data["projected_sphere_center"] = np.array(
                projected_sphere.center.to_list()
            )
            data["projected_sphere_axes"] = np.array(
                projected_sphere["axes"].to_list()
            )
            data["projected_sphere_angle"] = projected_sphere.angle

        if method == "3d":
            data["model_birth_timestamp"] = df["model_birth_timestamp"]
        elif method == "pye3d":
            data["location"] = np.array(df["location"].to_list())

        return data

    @staticmethod
    def _create_dataset(data, info, method):
        """ Create an xarray.Dataset from pupil data. """
        t = BaseReader._timestamps_to_datetimeindex(data["timestamp"], info)

        coords = {
            "time": t.values,
            "pixel_axis": ["x", "y"],
        }

        data_vars = {
            "eye": ("time", data["eye"]),
            "confidence": ("time", data["confidence"]),
            "diameter": ("time", data["diameter"]),
            "ellipse_angle": ("time", data["ellipse_angle"]),
            "pupil_norm_pos": (["time", "pixel_axis"], data["norm_pos"]),
            "ellipse_center": (["time", "pixel_axis"], data["ellipse_center"]),
            "ellipse_axes": (["time", "pixel_axis"], data["ellipse_axes"]),
        }

        # 3d only data
        if method in ("3d", "pye3d"):
            coords["cartesian_axis"] = ["x", "y", "z"]

            # 3d data
            for key in (
                "circle_center",
                "circle_normal",
                "sphere_center",
            ):
                data_vars[key] = (["time", "cartesian_axis"], data[key])

            # 2d data
            for key in (
                "projected_sphere_center",
                "projected_sphere_axes",
            ):
                data_vars[key] = (["time", "pixel_axis"], data[key])

            # 1d data
            for key in (
                "diameter_3d",
                "theta",
                "phi",
                "model_confidence",
                "circle_radius",
                "sphere_radius",
                "projected_sphere_angle",
            ):
                data_vars[key] = ("time", data[key])

        if method == "3d":
            data_vars["model_birth_timestamp"] = (
                "time",
                data["model_birth_timestamp"],
            )
        elif method == "pye3d":
            data_vars["location"] = (["time", "pixel_axis"], data["location"])

        ds = xr.Dataset(data_vars, coords)

        # sort and remove duplicate samples
        ds.sortby("time")
        _, index = np.unique(ds["time"], return_index=True)
        ds = ds.isel(time=index)

        return ds

    @staticmethod
    def _dataset_from_list(pupil_list, info, method):
        """ Create dataset from list of dicts. """
        df = pd.DataFrame(pupil_list)
        data = PupilReader._extract_pupil_data(df, method)
        ds = PupilReader._create_dataset(data, info, method)

        return ds

    def load_dataset(self):
        """ Load pupil data as an xarray Dataset.

        Returns
        -------
        xarray.Dataset
            The pupil data as a dataset.
        """
        if self.source == "recording":
            data = self._load_pupil(self.folder, self.method)
        elif self.source == "offline":
            data = self._load_pupil(
                self.folder / "offline_data", self.method, "offline_pupil"
            )
        else:
            raise ValueError(f"Invalid pupil source: {self.source}")

        return self._create_dataset(data, self.info, self.method)
