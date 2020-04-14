""""""
from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.utils import get_constructor_args
from pupil_recording_interface.externals.methods import normalize
from pupil_recording_interface.externals.file_methods import PLData_Writer


@process("pupil_detector")
class PupilDetector(BaseProcess):
    """ Pupil detector for eye video streams. """

    def __init__(
        self,
        method="2d c++",
        folder=None,
        record=False,
        camera_id=None,
        block=False,
        **kwargs,
    ):
        """ Constructor. """
        self.method = method
        self.folder = folder
        self.record = record
        self.camera_id = camera_id

        super().__init__(block=block, **kwargs)

        if self.method == "2d c++":
            from pupil_detectors import Detector2D

            self.detector = Detector2D()

        else:
            raise ValueError(f"Unsupported detection method: {self.method}")

        if self.record:
            if self.folder is None:
                raise ValueError("folder cannot be None")
            self.writer = PLData_Writer(self.folder, "pupil")
        else:
            self.writer = None

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(
            cls, config, folder=config.folder or kwargs.get("folder", None),
        )

        return cls(**cls_kwargs)

    def detect_pupil(self, packet):
        """"""
        frame = packet["frame"]
        pupil = self.detector.detect(frame)
        pupil["norm_pos"] = normalize(pupil["location"], frame.shape[2::-1])

        return pupil

    def record_data(self, packet):
        """"""
        # Hacky way of getting eye cam ID
        cam_id = self.camera_id or int(str(packet["device_uid"])[-1])

        datum = packet["pupil"].copy()
        datum["timestamp"] = packet.timestamp
        datum["topic"] = f"pupil.{cam_id}"
        datum["id"] = cam_id
        datum["method"] = self.method

        self.writer.append(datum)

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.pupil = self.call(self.detect_pupil, packet, block=block)
        if self.record:
            self.call(self.record_data, packet, block=block)

        packet.broadcasts.append("pupil")

        return packet

    def stop(self):
        """"""
        if self.writer is not None:
            self.writer.close()
