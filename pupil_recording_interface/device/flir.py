""""""
from datetime import datetime
import logging

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device.video import BaseVideoDevice
from pupil_recording_interface.utils import monotonic
from pupil_recording_interface.errors import DeviceNotConnected, IllegalSetting

logger = logging.getLogger(__name__)


def get_value(nodemap, node_name, value_type):
    """ Get a value from a nodemap. """
    import PySpin

    try:
        if value_type == "bool":
            node = PySpin.CBooleanPtr(nodemap.GetNode(node_name))
        elif value_type == "int":
            node = PySpin.CIntegerPtr(nodemap.GetNode(node_name))
        elif value_type == "float":
            node = PySpin.CFloatPtr(nodemap.GetNode(node_name))
        elif value_type == "str":
            node = PySpin.CStringPtr(nodemap.GetNode(node_name))
        else:
            raise ValueError(f"Unrecognized value type: {value_type}")

        return node.GetValue()

    except PySpin.SpinnakerException as e:
        raise ValueError(
            f"Could not get {node_name} of type {value_type}, reason: {e}"
        )


def set_value(nodemap, node_name, value):
    """ Set a value of a nodemap. """
    import PySpin

    try:
        # TODO check if we need to set string values
        if isinstance(value, str):
            node = PySpin.CEnumerationPtr(nodemap.GetNode(node_name))
            entry = node.GetEntryByName(value)
            node.SetIntValue(entry.GetValue())
        elif isinstance(value, bool):
            node = PySpin.CBooleanPtr(nodemap.GetNode(node_name))
            node.SetValue(value)
        elif isinstance(value, int):
            node = PySpin.CIntegerPtr(nodemap.GetNode(node_name))
            node.SetValue(value)
        elif isinstance(value, float):
            node = PySpin.CFloatPtr(nodemap.GetNode(node_name))
            node.SetValue(value)
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    except PySpin.SpinnakerException as e:
        raise IllegalSetting(
            f"Could not set {node_name} of type {type(value)} to {value}, "
            f"reason: {e}"
        )


class FLIRCapture:
    """ Capture wrapper for FLIR camera.

    This class is mostly required because of the questionable implementation
    of the Spinnaker Python wrapper, requiring the user to keep references
    to unused objects around to avoid dereferencing of the few C++ objects
    that are actually used.
    """

    def __init__(
        self, camera_type, camera, nodemap, system, timestamp_offset,
    ):
        """ Constructor. """
        self.camera_type = camera_type
        self.camera = camera
        self.nodemap = nodemap
        self.system = system
        self.timestamp_offset = timestamp_offset


@device("flir")
class VideoDeviceFLIR(BaseVideoDevice):
    """ FLIR video device. """

    def __init__(
        self,
        device_uid,
        resolution,
        fps,
        exposure_value=None,
        gain=None,
        settings=None,
    ):
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
        # TODO specify additional keyword arguments
        super(VideoDeviceFLIR, self).__init__(
            device_uid,
            resolution,
            fps,
            exposure_value=exposure_value,
            gain=gain,
            settings=settings,
        )

        self.timebase = "epoch"

    @classmethod
    def _compute_timestamp_offset(cls, cam, number_of_iterations, camera_type):
        """ Gets timestamp offset in seconds from input camera """

        import statistics

        # This method is required because the timestamp stored in the camera is
        # relative to when it was powered on, so an offset needs to be applied
        # to get it into epoch time; from tests I've done, this appears to be
        # accurate to ~1e-3 seconds.
        logger.debug("Measuring TimeStamp Offset ...")
        timestamp_offsets = []

        for i in range(number_of_iterations):
            # Latch timestamp. This basically "freezes" the current camera
            # timer into a variable that can be read with TimestampLatchValue()
            cam.TimestampLatch.Execute()

            # Compute timestamp offset in seconds; note that timestamp latch
            # value is in nanoseconds

            if camera_type == "BlackFly":
                timestamp_offset = (
                    datetime.now().timestamp()
                    - cam.TimestampLatchValue.GetValue() / 1e9
                )
            elif camera_type == "Chameleon":
                timestamp_offset = (
                    datetime.now().timestamp() - cam.Timestamp.GetValue() / 1e9
                )
            else:
                raise ValueError(f"Invalid camera type: {camera_type}")

            # Append
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

        logger.debug("*** DEVICE INFORMATION ***\n")

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
    def get_camera(cls, serial_number, system):
        """ Get camera by serial number """
        import PySpin

        cam_list = system.GetCameras()
        logger.debug(f"Number of cameras detected: {cam_list.GetSize()}")
        if serial_number is not None:
            try:
                camera = cam_list.GetBySerial(0)
            except PySpin.SpinnakerException:
                cam_list.Clear()
                raise DeviceNotConnected(
                    f"Camera with serial number {serial_number} not connected"
                )
        else:
            try:
                camera = cam_list.GetByIndex(0)
            except PySpin.SpinnakerException:
                cam_list.Clear()
                raise DeviceNotConnected(f"No FLIR cameras connected")

        return camera

    @classmethod
    def get_capture(
        cls,
        serial_number,
        resolution,
        fps,
        exposure_value=None,
        gain=None,
        settings=None,
    ):
        """ Get a capture instance for a device by name. """
        import PySpin

        system = PySpin.System.GetInstance()

        # initialize camera
        camera = cls.get_camera(serial_number, system)
        camera.Init()
        nodemap = camera.GetNodeMap()
        device_nodemap = camera.GetTLDeviceNodeMap()
        stream_nodemap = camera.GetTLStreamNodeMap()

        # get model
        device_model = get_value(nodemap, "DeviceModelName", "str")
        if "Chameleon" in device_model:
            camera_type = "Chameleon"
        elif "Blackfly" in device_model:
            camera_type = "BlackFly"
        else:
            raise ValueError(f"Invalid camera type: {device_model}")

        # log device info
        logger.debug(f"FLIR camera type: {camera_type}")
        cls._log_device_info(device_nodemap)

        # disable trigger mode
        camera.TriggerMode.SetValue(PySpin.TriggerMode_Off)

        if camera_type == "Chameleon":

            # set gain
            if gain is not None:
                set_value(nodemap, "GainAuto", "Off")
                set_value(nodemap, "Gain", float(gain))

            # set exposure time
            if exposure_value is not None:
                camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                exposure_value = min(
                    camera.ExposureTime.GetMax(), exposure_value
                )
                camera.ExposureTime.SetValue(exposure_value)
                logger.debug(
                    f"Exposure time: {camera.ExposureTime.GetValue()}"
                )

            # set frame rate
            set_value(nodemap, "AcquisitionMode", "Continuous")
            set_value(nodemap, "AcquisitionFrameRateAuto", "Off")
            set_value(nodemap, "AcquisitionFrameRateEnabled", True)
            set_value(nodemap, "AcquisitionFrameRate", float(fps))
            logger.debug(f"Set FLIR fps to: {fps}")

        elif camera_type == "BlackFly":
            camera.AcquisitionFrameRateEnable.SetValue(True)
            camera.AcquisitionFrameRate.SetValue(float(fps))
            logger.debug(f"Set FLIR fps to: {fps}")

        # TODO: Find a way of reading the actual frame rate for Chameleon
        #  Chameleon doesn't have this register or anything similar to this
        if camera_type == "BlackFly":
            logger.debug(
                f"Actual frame rate: "
                f"{camera.AcquisitionResultingFrameRate.GetValue()}",
            )

        # set pixel format
        set_value(nodemap, "PixelFormat", "BayerRG8")

        # get only last image from buffer to avoid delay
        set_value(stream_nodemap, "StreamBufferHandlingMode", "NewestOnly")

        # set other settings from kwargs
        for setting, value in (settings or {}).items():
            logger.debug(f"Setting {setting} to {value}")
            set_value(nodemap, setting, value)

        # compute timestamp offset
        timestamp_offset = cls._compute_timestamp_offset(
            camera, 20, camera_type
        )
        logger.debug(f"Timestamp offset: {timestamp_offset / 1e9}")

        #  begin acquisition
        camera.BeginAcquisition()
        logger.debug("Acquisition started")

        return FLIRCapture(
            camera_type, camera, nodemap, system, timestamp_offset
        )

    def stop(self):
        """ Stop the device. """
        self.capture.camera.AcquisitionStop()
        logger.debug("Stopped FLIR camera")

    def get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        import PySpin

        try:
            #  Retrieve next received image
            image = self.capture.camera.GetNextImage()

            timestamp = monotonic()

            # TODO: Image Pointer doesn't have any GetTimeStamp() attribute
            #  timestamp = float(image.GetTimestamp()) / 1e9
            # TODO: Temporary solution to fix the FLIR timestamp issue
            self.capture.camera.TimestampLatch.Execute()
            if self.capture.camera_type == "BlackFly":
                source_timestamp = (
                    self.capture.timestamp_offset
                    + self.capture.camera.TimestampLatchValue.GetValue() / 1e9
                )
            elif self.capture.camera_type == "Chameleon":
                source_timestamp = (
                    self.capture.timestamp_offset
                    + self.capture.camera.Timestamp.GetValue() / 1e9
                )
            else:
                raise RuntimeError(
                    f"Invalid camera type: {self.capture.camera_type}"
                )

            #  Ensure image completion
            if image.IsIncomplete():
                # TODO check if this is a valid way of handling an
                #  incomplete image
                logger.warning("Image incomplete")
                return self.get_frame_and_timestamp(mode)
            else:
                if mode == "img":
                    frame = image.Convert(
                        PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR
                    )
                elif mode == "gray":
                    frame = image.Convert(
                        PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR
                    )
                else:
                    raise RuntimeError(f"Unsupported mode: {mode}")
                image.Release()

            frame = frame.GetNDArray()

        except PySpin.SpinnakerException as ex:
            # TODO check correct error handling
            raise ValueError(ex)

        return frame, timestamp, source_timestamp
