""""""
import logging

import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.packet import Packet
from pupil_recording_interface.reader.pupil import PupilReader
from pupil_recording_interface.externals.methods import normalize
from pupil_recording_interface.externals.file_methods import PLData_Writer

logger = logging.getLogger(__name__)


@process("pupil_detector")
class PupilDetector(BaseProcess):
    """ Pupil detector for eye video streams. """

    def __init__(
        self,
        method="2d c++",
        camera_id=None,
        resolution=None,
        focal_length=None,
        folder=None,
        record=False,
        display=True,
        **kwargs,
    ):
        """ Constructor. """
        self.method = method
        self.camera_id = camera_id
        self.resolution = resolution
        self.focal_length = focal_length
        self.folder = folder
        self.record = record
        self.display = display

        super().__init__(**kwargs)

        if self.method not in ("2d c++", "pye3d"):
            raise ValueError(f"Unsupported detection method: {self.method}")
        if self.method == "pye3d" and (
            self.resolution is None or self.focal_length is None
        ):
            raise ValueError(
                "Resolution and focal length must be specified for pye3d"
            )

        self.detector = None
        self.detector_pye3d = None
        self.writer = None

        if self.record and self.folder is None:
            raise ValueError("folder cannot be None")

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = cls._get_constructor_args(
            config, folder=config.folder or kwargs.get("folder", None),
        )

        if cls_kwargs["camera_id"] is None:
            try:
                cls_kwargs["camera_id"] = int(stream_config.name[-1])
            except (ValueError, TypeError):
                try:
                    cls_kwargs["camera_id"] = int(stream_config.device_uid[-1])
                except (ValueError, TypeError):
                    logger.debug("Could not auto-determine eye camera ID")

        # TODO focal length and resolution

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process. """
        if self.method == "2d c++":
            from pupil_detectors import Detector2D

            self.detector = Detector2D()

        elif self.method == "pye3d":
            from pupil_detectors import Detector2D
            from pye3d.camera import CameraModel
            from pye3d.detector_3d import Detector3D

            camera = CameraModel(self.focal_length, self.resolution)
            self.detector = Detector2D()
            self.detector_pye3d = Detector3D(camera)

        else:
            raise ValueError(f"Unsupported detection method: {self.method}")

        if self.record:
            self.writer = PLData_Writer(self.folder, "pupil")

    def stop(self):
        """ Stop the process. """
        self.detector = None
        self.detector_pye3d = None

        if self.writer is not None:
            self.writer.close()
            self.writer = None

    def display_hook(self, packet):
        """ Add pupil overlay onto frame. """
        pupil = packet["pupil"]
        if pupil is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        ellipse = pupil["ellipse"]
        cv2.ellipse(
            frame,
            tuple(int(v) for v in ellipse["center"]),
            tuple(int(v / 2) for v in ellipse["axes"]),
            ellipse["angle"],
            0,
            360,  # start/end angle for drawing
            (0, 0, 255),  # color (BGR): red
        )

        return frame

    def _process_packet(self, packet):
        """ Process a new packet. """
        packet.pupil = self.detect_pupil(packet)

        if self.record:
            self.record_data(packet)

        packet.broadcasts.append("pupil")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet

    def detect_pupil(self, packet):
        """ Detect pupil in frame. """
        frame = packet["frame"]

        if frame.ndim == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        pupil = self.detector.detect(frame)

        pupil["norm_pos"] = normalize(pupil["location"], frame.shape[1::-1])
        pupil["timestamp"] = packet["timestamp"]
        pupil["method"] = self.method
        pupil["id"] = self.camera_id
        pupil["topic"] = (
            f"pupil.{self.camera_id}" if self.camera_id else "pupil"
        )

        # second pass for pye3d detector
        if self.method == "pye3d":
            pupil_3d = self.detector_pye3d.update_and_detect(pupil, frame)
            pupil.update(pupil_3d)

        return pupil

    def record_data(self, packet):
        """ Write pupil datum to disk. """
        self.writer.append(packet["pupil"])

    def batch_run(
        self, video_reader, start=None, end=None, return_type="list"
    ):
        """ Detect pupils in an eye video.

        Parameters
        ----------
        video_reader : pri.VideoReader instance
            Video reader for an eye camera recording.

        start : int or pandas.Timestamp, optional
            If specified, start the detection at this frame index or timestamp.

        end : int or pandas.Timestamp, optional
            If specified, stop the detection at this frame index or timestamp.

        return_type : str or None, default "list"
            The data type that this method should return. "list" returns o list
            of dicts with pupil data for each frame. "dataset" returns an
            xarray Dataset. Can also be None, in that case pupil data is not
            loaded into memory and this method returns nothing, which is useful
            when recording detected pupils to disk.

        Returns
        -------
        pupil_list : list of dict
            List of detected pupils if return_type="list" (one per frame).

        ds : xarray.Dataset
            Dataset with pupil data if return_type="dataset".
        """
        if return_type not in ("list", "dataset", None):
            raise ValueError(
                f"return_type can be 'list', 'dataset' or None, "
                f"got {return_type}"
            )

        pupil_list = []

        # the video reader timestamps are datetime values but pupil timestamps
        # should be monotonic
        monotonic_offset = (
            video_reader.info["start_time_synced_s"]
            - video_reader.info["start_time_system_s"]
        )

        with self:
            for frame, ts in video_reader.read_frames(
                start, end, raw=True, return_timestamp=True
            ):
                ts = float(ts.value) / 1e9 + monotonic_offset
                packet = Packet(
                    "video_reader", "video_reader", ts, frame=frame,
                )
                packet.pupil = self.detect_pupil(packet)

                if return_type is not None:
                    pupil_list.append(packet.pupil)

                if self.record:
                    self.record_data(packet)

        if return_type == "list":
            return pupil_list
        elif return_type == "dataset":
            # only the stem of the method (e.g. 2d instead of 2d c++)
            method = self.method.split()[0]
            return PupilReader._dataset_from_list(
                pupil_list, video_reader.info, method
            )
