""""""
import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.packet import Packet
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.reader.marker import MarkerReader
from pupil_recording_interface.externals.circle_detector import CircleTracker


@process("circle_detector")
class CircleDetector(BaseProcess):
    """ Circle detector for the world video stream. """

    def __init__(
        self,
        scale=0.5,
        detection_method="pupil",
        marker_size=(12, 300),
        threshold_window_size=13,
        min_area=500,
        max_area=1000,
        circularity=0.8,
        convexity=0.7,
        inertia=0.4,
        display=True,
        **kwargs,
    ):
        """ Constructor. """
        super().__init__(**kwargs)

        self.circle_tracker = CircleTracker(
            scale=scale,
            detection_method=detection_method,
            marker_size=marker_size,
            threshold_window_size=threshold_window_size,
            min_area=min_area,
            max_area=max_area,
            circularity=circularity,
            convexity=convexity,
            inertia=inertia,
            **kwargs,
        )
        self.scale = scale
        self.display = display

    def display_hook(self, packet):
        """ Add gaze overlay onto frame. """
        circle_markers = packet["circle_markers"]
        if circle_markers is None:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame

        if len(circle_markers) == 0:
            # Return the attribute to avoid unnecessary waiting
            return packet.display_frame
        else:
            # TODO get the largest marker
            marker_position = (
                int(circle_markers[0]["img_pos"][0]),
                int(circle_markers[0]["img_pos"][1]),
            )

        frame = packet["display_frame"]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # TODO make constructor arguments
        # TODO Define color, radius and thickness in config
        color = (0, 0, 255)
        marker_thickness = 5
        radius = 20

        cv2.circle(
            frame, marker_position, radius, color, thickness=marker_thickness
        )

        return frame

    def _process_packet(self, packet):
        """ Process a new packet. """
        packet.circle_markers = self.detect_circle(packet)

        packet.broadcasts.append("circle_markers")

        if self.display:
            packet.display_hooks.append(self.display_hook)

        return packet

    def detect_circle(self, packet):
        """ Detect circle markers. """
        frame = packet["frame"]

        if packet.color_format == "bgr24":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif packet.color_format == "bggr8":
            frame = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2GRAY)
        circle_markers = self.circle_tracker.update(frame)

        for marker in circle_markers:
            marker["timestamp"] = packet.timestamp

        return circle_markers

    def batch_run(
        self, video_reader, start=None, end=None, return_type="list"
    ):
        """ Detect reference markers in a world video.

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
        marker_list : list of dict
            List of detected markers if return_type="list".

        ds : xarray.Dataset
            Dataset with marker data if return_type="dataset".
        """
        if return_type not in ("list", "dataset", None):
            raise ValueError(
                f"return_type can be 'list', 'dataset' or None, "
                f"got {return_type}"
            )

        marker_list = []

        # the video reader timestamps are datetime values but marker timestamps
        # should be monotonic
        monotonic_offset = (
            video_reader.info["start_time_synced_s"]
            - video_reader.info["start_time_system_s"]
        )

        with self:
            for frame, ts, idx in video_reader.read_frames(
                start, end, raw=True, return_timestamp=True, return_index=True
            ):
                ts = float(ts.value) / 1e9 + monotonic_offset
                packet = Packet(
                    "video_reader",
                    "video_reader",
                    ts,
                    frame=frame,
                    color_format="bgr24",
                )
                circle_markers = self.detect_circle(packet)

                if circle_markers is None or len(circle_markers) == 0:
                    continue

                if return_type is not None:
                    marker = circle_markers[0]
                    marker["frame_index"] = idx
                    marker_list.append(marker)

        if return_type == "list":
            return marker_list
        elif return_type == "dataset":
            return MarkerReader._dataset_from_list(
                marker_list, video_reader.info
            )
