""""""
import time
import statistics
import logging

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device.video import BaseVideoDevice
from pupil_recording_interface.utils import monotonic
from pupil_recording_interface.errors import DeviceNotConnected, IllegalSetting

logger = logging.getLogger(__name__)


class Nodemap:
    def __init__(self, camera, nodemap="camera"):
        """ Constructor. """
        if nodemap == "camera":
            self._nodemap = camera.GetNodeMap()
        elif nodemap == "device":
            self._nodemap = camera.GetTLDeviceNodeMap()
        elif nodemap == "stream":
            self._nodemap = camera.GetTLStreamNodeMap()
        else:
            raise ValueError(f"Unknown nodemap: {nodemap}")

    def get_value(self, node_name, value_type):
        """ Get a value from a nodemap. """
        import PySpin

        try:
            if value_type == "bool":
                node = PySpin.CBooleanPtr(self._nodemap.GetNode(node_name))
            elif value_type == "int":
                node = PySpin.CIntegerPtr(self._nodemap.GetNode(node_name))
            elif value_type == "float":
                node = PySpin.CFloatPtr(self._nodemap.GetNode(node_name))
            elif value_type == "str":
                node = PySpin.CStringPtr(self._nodemap.GetNode(node_name))
            else:
                raise ValueError(f"Unrecognized value type: {value_type}")

            return node.GetValue()

        except PySpin.SpinnakerException as e:
            raise ValueError(
                f"Could not get {node_name} of type {value_type}, reason: {e}"
            )

    def set_value(self, node_name, value):
        """ Set a value of a nodemap. """
        import PySpin

        try:
            # TODO check if we need to set string values
            if isinstance(value, str):
                node = PySpin.CEnumerationPtr(self._nodemap.GetNode(node_name))
                entry = node.GetEntryByName(value)
                node.SetIntValue(entry.GetValue())
            elif isinstance(value, bool):
                node = PySpin.CBooleanPtr(self._nodemap.GetNode(node_name))
                node.SetValue(value)
            elif isinstance(value, int):
                node = PySpin.CIntegerPtr(self._nodemap.GetNode(node_name))
                node.SetValue(value)
            elif isinstance(value, float):
                node = PySpin.CFloatPtr(self._nodemap.GetNode(node_name))
                node.SetValue(value)
            else:
                raise ValueError(f"Unsupported value type: {type(value)}")

        except PySpin.SpinnakerException as e:
            raise IllegalSetting(
                f"Could not set {node_name} of type {type(value)} to {value}, "
                f"reason: {e}"
            )


@device("flir")
class VideoDeviceFLIR(BaseVideoDevice):
    """ FLIR video device. """

    def __init__(self, device_uid, resolution, fps, settings=None):
        """ Constructor.

        Parameters
        ----------
        device_uid: str
            The serial number of the device. If None, will use the first
            camera in the Spinnaker device list.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.
        """
        super(VideoDeviceFLIR, self).__init__(
            device_uid, resolution, fps, settings=settings
        )

        self.timebase = "epoch"

    @classmethod
    def _compute_timestamp_offset(cls, cam, n_iterations):
        """ Gets timestamp offset in seconds from input camera.

        This method is required because the timestamp stored in the camera is
        relative to when it was powered on, so an offset needs to be applied
        to get it into epoch time; from tests I've done, this appears to be
        accurate to ~1e-3 seconds.
        """
        logger.debug("Measuring timestamp offset ...")
        timestamp_offsets = []

        for i in range(n_iterations):
            # Latch timestamp. This basically "freezes" the current camera
            # timer into a variable that can be read with TimestampLatchValue()
            cam.TimestampLatch.Execute()

            # Compute timestamp offset in seconds; note that timestamp latch
            # value is in nanoseconds
            try:
                timestamp_offset = time.time() - cam.Timestamp.GetValue() / 1e9
            except AttributeError:
                timestamp_offset = (
                    time.time() - cam.TimestampLatchValue.GetValue() / 1e9
                )

            timestamp_offsets.append(timestamp_offset)

        # Return the median value
        return statistics.median(timestamp_offsets)

    @classmethod
    def _log_device_info(cls, nodemap):
        """
        This function prints the device information of the camera from the
        transport layer; please see NodeMapInfo example for more in-depth
        comments on printing device information from the nodemap.
        """
        import PySpin

        try:
            node_device_information = PySpin.CCategoryPtr(
                nodemap.GetNode("DeviceInformation")
            )

            if PySpin.IsAvailable(
                node_device_information
            ) and PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = PySpin.CValuePtr(feature)
                    logger.debug(
                        "{}: {}".format(
                            node_feature.GetName(),
                            node_feature.ToString()
                            if PySpin.IsReadable(node_feature)
                            else "Node not readable",
                        )
                    )

            else:
                logger.debug("Device control information not available.")

        except PySpin.SpinnakerException as ex:
            logger.error(str(ex))

    @classmethod
    def get_capture(cls, serial_number, resolution, fps, settings=None):
        """ Get a capture instance for a device by name. """
        import PySpin
        from simple_pyspin import Camera, CameraError

        try:
            camera = Camera(serial_number or 0, lock=False)
        except CameraError as e:
            raise DeviceNotConnected(str(e))

        # initialize camera
        camera.init()
        camera.nodemap = Nodemap(camera.cam)
        camera.stream_nodemap = Nodemap(camera.cam, "stream")
        camera.device_nodemap = Nodemap(camera.cam, "device")

        # get model
        device_model = camera.device_nodemap.get_value(
            "DeviceModelName", "str"
        )
        if "Chameleon" in device_model:
            camera.camera_type = "Chameleon"
        elif "Blackfly" in device_model:
            camera.camera_type = "BlackFly"
        else:
            raise ValueError(f"Invalid camera type: {device_model}")

        # log device info
        logger.debug(f"FLIR camera type: {camera.camera_type}")
        cls._log_device_info(camera.device_nodemap._nodemap)

        # disable trigger mode
        camera.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)

        # set frame rate
        # TODO set auto frame rate if fps is None
        logger.debug(
            f"Setting {camera.camera_type}:AcquisitionFrameRate to {fps}"
        )
        if camera.camera_type == "Chameleon":
            camera.nodemap.set_value("AcquisitionMode", "Continuous")
            camera.nodemap.set_value("AcquisitionFrameRateAuto", "Off")
            camera.nodemap.set_value("AcquisitionFrameRateEnabled", True)
            camera.nodemap.set_value("AcquisitionFrameRate", float(fps))
        elif camera.camera_type == "BlackFly":
            camera.cam.AcquisitionFrameRateEnabled.SetValue(True)
            camera.cam.AcquisitionFrameRate.SetValue(float(fps))
            # TODO: Find a way of reading the actual frame rate for
            #  Chameleon which doesn't have this register or anything
            #  similar to this
            logger.debug(
                f"Actual frame rate: "
                f"{camera.cam.AcquisitionResultingFrameRate}",
            )

        # set pixel format
        camera.nodemap.set_value("PixelFormat", "BayerRG8")

        # get only last image from buffer to avoid delay
        camera.stream_nodemap.set_value(
            "StreamBufferHandlingMode", "NewestOnly"
        )

        # set other settings
        for setting, value in (settings or {}).items():
            logger.debug(f"Setting {camera.camera_type}:{setting} to {value}")
            try:
                setattr(camera, setting, value)
            except (
                AttributeError,
                NotImplementedError,
                PySpin.SpinnakerException,
            ):
                camera.nodemap.set_value(setting, value)

        # compute timestamp offset
        camera.timestamp_offset = cls._compute_timestamp_offset(camera.cam, 20)
        logger.debug(f"Timestamp offset: {camera.timestamp_offset / 1e9}")

        #  begin acquisition
        camera.start()
        logger.debug("Acquisition started")

        return camera

    def start(self):
        """ Start the device. """
        super().start()
        self.device_uid = self.device_uid or self.capture.nodemap.get_value(
            "DeviceSerialNumber", "str"
        )

    def stop(self):
        """ Stop the device. """
        import PySpin

        try:
            self.capture.cam.EndAcquisition()
        except PySpin.SpinnakerException as e:
            logger.debug(f"Could not stop camera: {e}")
        try:
            self.capture.cam.DeInit()
        except PySpin.SpinnakerException as e:
            logger.debug(f"Could not de-init camera: {e}")
        del self.capture.cam

        self.capture = None
        logger.debug("Stopped FLIR camera")

    def get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        import PySpin

        try:
            # Retrieve next received image
            image = self.capture.get_image()
            self.capture.cam.TimestampLatch.Execute()

            timestamp = monotonic()
            try:
                source_timestamp = (
                    self.capture.timestamp_offset
                    + self.capture.Timestamp / 1e9
                )
            except AttributeError:
                source_timestamp = (
                    self.capture.timestamp_offset
                    + self.capture.TimestampLatchValue / 1e9
                )

            #  Ensure image completion
            if image.IsIncomplete():
                # TODO check if this is a valid way of handling an
                #  incomplete image
                logger.warning("Image incomplete")
                return self.get_frame_and_timestamp(mode)
            else:
                image.Release()
                if mode in ("bgr24", "img"):
                    frame = image.Convert(
                        PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR
                    )
                elif mode == "gray":
                    frame = image.Convert(
                        PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR
                    )
                elif mode == "bayer_rggb8":
                    frame = image
                else:
                    raise RuntimeError(f"Unsupported mode: {mode}")

            frame = frame.GetNDArray()

        except PySpin.SpinnakerException as e:
            logger.error(
                f"{self.device_type} device {self.device_uid} "
                f"streaming error: {e}"
            )
            self.restart()
            return self.get_frame_and_timestamp(mode)

        return frame, timestamp, source_timestamp
