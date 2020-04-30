""""""
from datetime import datetime
import logging

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device.video import BaseVideoDevice
from pupil_recording_interface.utils import monotonic
from pupil_recording_interface.errors import DeviceNotConnected

logger = logging.getLogger(__name__)


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
        self, device_uid, resolution, fps, exposure_value=31000.0, gain=18,
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
    def get_capture(
        cls, serial_number, resolution, fps, exposure_value=31000.0, gain=18
    ):
        """ Get a capture instance for a device by name. """
        import PySpin

        system = PySpin.System.GetInstance()

        # Get camera by serial number
        cam_list = system.GetCameras()
        logger.debug(f"Number of cameras detected: {cam_list.GetSize()}")

        for camera in cam_list:
            device_nodemap = camera.GetTLDeviceNodeMap()
            node_device_serial_number = PySpin.CStringPtr(
                device_nodemap.GetNode("DeviceSerialNumber")
            )
            if PySpin.IsAvailable(
                node_device_serial_number
            ) and PySpin.IsReadable(node_device_serial_number):
                # return camera instance if serial number matches
                if (
                    serial_number is None
                    or node_device_serial_number.GetValue() == serial_number
                ):
                    break
            else:
                logger.warning(
                    f"Could not get serial number for camera {camera}"
                )
        else:
            cam_list.Clear()
            raise DeviceNotConnected(
                f"Camera with serial number {serial_number} not connected"
            )

        logger.debug(f"FLIR Camera : {camera}")
        cls._log_device_info(device_nodemap)

        # Initialize camera
        camera.Init()

        camera.TriggerMode.SetValue(PySpin.TriggerMode_Off)

        # Retrieve GenICam nodemap
        nodemap = camera.GetNodeMap()
        device_model = PySpin.CStringPtr(
            nodemap.GetNode("DeviceModelName")
        ).GetValue()

        if "Chameleon" in device_model:
            camera_type = "Chameleon"
        elif "Blackfly" in device_model:
            camera_type = "BlackFly"
        else:
            raise ValueError(f"Invalid camera type: {device_model}")

        logger.debug(f"FLIR Camera Type = {camera_type}")

        if camera_type == "Chameleon":
            logger.debug("Initializing Chameleon ...")

            # TODO: Read these settings from yaml file
            #  if camera.ExposureAuto.GetAccessMode() != PySpin.RW:
            #      logger.debug("Unable to disable automatic exposure.
            #      Aborting...")
            #      return False
            #  camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
            #  logger.debug("Automatic exposure disabled...")
            #  if camera.ExposureTime.GetAccessMode() != PySpin.RW:
            #      logger.debug("Unable to set exposure time. Aborting...")
            #      return False
            #  node_GainAuto = PySpin.CEnumerationPtr(
            #                    nodemap.GetNode("GainAuto"))
            #  node_GainAuto_off = node_GainAuto.GetEntryByName("Off")
            #  node_GainAuto.SetIntValue(node_GainAuto_off.GetValue())
            #  node_Gain = PySpin.CFloatPtr(nodemap.GetNode("Gain"))
            #  node_Gain.SetValue(gain)
            #  logger.debug('gain set to: ', node_Gain.GetValue())

            # disable auto frame rate
            auto_frame_rate_node = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionFrameRateAuto")
            )
            auto_frame_rate_node.SetIntValue(
                auto_frame_rate_node.GetEntryByName("Off").GetValue()
            )

            # set frame rate
            PySpin.CBooleanPtr(
                nodemap.GetNode("AcquisitionFrameRateEnabled")
            ).SetValue(True)
            frame_rate_node = PySpin.CFloatPtr(
                nodemap.GetNode("AcquisitionFrameRate")
            )
            frame_rate_node.SetValue(fps)
            logger.debug(f"fps set to: {frame_rate_node.GetValue()}")

            # TODO Ensure desired exposure time does not exceed the maximum
            #  exposure_time_to_set = exposure_value
            #  exposure_time_to_set = min(camera.ExposureTime.GetMax(),
            #                             exposure_time_to_set)
            #  camera.ExposureTime.SetValue(exposure_time_to_set)
            #  logger.debug('exposure set to: ',
            #  camera.ExposureTime.GetValue())

        elif camera_type == "BlackFly":
            logger.debug("Initializing BlackFly ...")
            camera.AcquisitionFrameRateEnable.SetValue(True)
            camera.AcquisitionFrameRate.SetValue(float(fps))

        logger.debug(f"Set FLIR fps to: {fps}")

        # Set Pixel Format to RGB8
        node_pixel_format = PySpin.CEnumerationPtr(
            nodemap.GetNode("PixelFormat")
        )
        if not PySpin.IsAvailable(node_pixel_format) or not PySpin.IsWritable(
            node_pixel_format
        ):
            logger.warning(
                "Unable to set Pixel Format to RGB8 (enum retrieval)"
            )

        node_pixel_format_RGB8 = node_pixel_format.GetEntryByName("RGB8")
        if not PySpin.IsAvailable(
            node_pixel_format_RGB8
        ) or not PySpin.IsReadable(node_pixel_format_RGB8):
            logger.warning(
                "Unable to set Pixel Format to RGB8 (entry retrieval)"
            )

        pixel_format_RGB8 = node_pixel_format_RGB8.GetValue()
        node_pixel_format.SetIntValue(pixel_format_RGB8)

        # get only last image from buffer to avoid delay
        stream_nodemap = camera.GetTLStreamNodeMap()
        handling_mode = PySpin.CEnumerationPtr(
            stream_nodemap.GetNode("StreamBufferHandlingMode")
        )
        handling_mode_entry = handling_mode.GetEntryByName("NewestOnly")
        handling_mode.SetIntValue(handling_mode_entry.GetValue())
        logger.debug(
            f"Set FLIR buffer handling to: NewestOnly: "
            f"{handling_mode_entry.GetValue()}",
        )

        # TODO: Find a way of reading the actual frame rate for Chameleon
        #  Chameleon doesn't have this register or anything similar to this
        if camera_type == "BlackFly":
            logger.debug(
                f"Actual frame rate: "
                f"{camera.AcquisitionResultingFrameRate.GetValue()}",
            )

        timestamp_offset = cls._compute_timestamp_offset(
            camera, 20, camera_type
        )
        logger.debug(f"TimeStamp offset: {timestamp_offset / 1e9}")

        #  Begin acquiring images
        camera.BeginAcquisition()
        logger.debug("Acquisition started!")

        return FLIRCapture(
            camera_type, camera, nodemap, system, timestamp_offset
        )

    def stop(self):
        """ Stop the device. """
        self.capture.camera.AcquisitionStop()
        logger.debug("Stopped FLIR camera")

    def get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        # TODO return grayscale frame if mode=='gray'
        import PySpin

        try:
            #  Retrieve next received image
            image_result = self.capture.camera.GetNextImage()

            timestamp = monotonic()

            # TODO: Image Pointer doesn't have any GetTimeStamp() attribute
            #  timestamp = float(image_result.GetTimestamp()) / 1e9
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
            if image_result.IsIncomplete():
                # TODO check if this is a valid way of handling an
                #  incomplete image
                logger.warning("Image Incomplete!")
                return self.get_frame_and_timestamp(mode)

            else:
                frame = image_result.Convert(
                    PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR
                )

                #  Release image
                image_result.Release()

        except PySpin.SpinnakerException as ex:
            # TODO check correct error handling
            raise ValueError(ex)

        # TODO: return both pupil and FLIR timestamp
        return frame.GetNDArray(), timestamp, source_timestamp
