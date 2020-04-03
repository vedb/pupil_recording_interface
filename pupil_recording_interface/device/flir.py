""""""
from datetime import datetime
import logging

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device.video import BaseVideoDevice

logger = logging.getLogger(__name__)


class FLIRCapture(object):
    """ Capture wrapper for FLIR camera. """

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
            The unique identity of this device. Depending on the device this
            will be a serial number or similar.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        start: bool, default True
            If True, initialize the underlying capture upon construction.
            Set to False for multi-threaded recording.
        """
        # TODO specify additional keyword arguments
        super(VideoDeviceFLIR, self).__init__(
            device_uid,
            resolution,
            fps,
            exposure_value=exposure_value,
            gain=gain,
        )

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
    def _get_capture(
        cls, uid, resolution, fps, exposure_value=31000.0, gain=18
    ):
        """ Get a capture instance for a device by name. """
        import PySpin

        system = PySpin.System.GetInstance()

        # Retrieve list of cameras from the system
        cam_list = system.GetCameras()
        logger.debug("List of Cameras: ", cam_list)
        num_cameras = cam_list.GetSize()
        logger.debug(f"Number of cameras detected: {num_cameras}")

        # Finish if there are no cameras
        if num_cameras == 0:
            cam_list.Clear()
            system.ReleaseInstance()
            raise ValueError("Not enough cameras!")

        # TODO: Use uid to identify camera
        camera = cam_list[0]
        logger.debug("FLIR Camera : ", camera)

        # Initialize camera
        camera.Init()

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = camera.GetTLDeviceNodeMap()
        nodemap_tlstream = camera.GetTLStreamNodeMap()
        cls._log_device_info(nodemap_tldevice)

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

        logger.debug("FLIR Camera Type = ", camera_type)

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
            logger.debug("fps set to: ", frame_rate_node.GetValue())

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
            camera.AcquisitionFrameRate.SetValue(fps)
        else:
            raise ValueError(f"Invalid camera type: {camera_type}")

        logger.debug("Set FLIR fps to:", fps)

        buffer_handling_node = PySpin.CEnumerationPtr(
            nodemap_tlstream.GetNode("buffer_handling_node")
        )
        buffer_handling_node_entry = buffer_handling_node.GetEntryByName(
            "NewestOnly"
        )
        buffer_handling_node.SetIntValue(buffer_handling_node_entry.GetValue())
        logger.debug(
            "Set FLIR buffer handling to: NewestOnly: ",
            buffer_handling_node_entry.GetValue(),
        )

        # TODO: Find a way of reading the actual frame rate for Chameleon
        #  Chameleon doesn't have this register or anything similar to this
        if camera_type == "BlackFly":
            logger.debug(
                "Actual frame rate: ",
                camera.AcquisitionResultingFrameRate.GetValue(),
            )

        timestamp_offset = cls._compute_timestamp_offset(
            camera, 20, camera_type
        )
        logger.debug("TimeStamp offset: ", timestamp_offset / 1e9)

        #  Begin acquiring images
        camera.BeginAcquisition()
        logger.debug("Acquisition started!")

        return FLIRCapture(
            camera_type, camera, nodemap, system, timestamp_offset
        )

    def _get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        # TODO return grayscale frame if mode=='gray'
        import PySpin
        import uvc

        try:
            #  Retrieve next received image
            image_result = self.capture.GetNextImage()

            # TODO: Make sure there is no harm reading uvc time stamp
            uvc_timestamp = uvc.get_time_monotonic()

            # TODO: Image Pointer doesn't have any GetTimeStamp() attribute
            #  timestamp = float(image_result.GetTimestamp()) / 1e9
            # TODO: Temporary solution to fix the FLIR timestamp issue
            self.capture.TimestampLatch.Execute()
            if self.capture.camera_type == "BlackFly":
                timestamp = (
                    self.capture.timestamp_offset
                    + self.capture.TimestampLatchValue.GetValue() / 1e9
                )
            elif self.capture.camera_type == "Chameleon":
                timestamp = (
                    self.capture.timestamp_offset
                    + self.capture.Timestamp.GetValue() / 1e9
                )
            else:
                raise ValueError(
                    f"Invalid camera type: {self.capture.camera_type}"
                )

            #  Ensure image completion
            if image_result.IsIncomplete():
                # TODO check if this is a valid way of handling an
                #  incomplete image
                logger.warning("Image Incomplete!")
                return self._get_frame_and_timestamp(mode)

            else:
                frame = image_result.Convert(
                    PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR
                )

                #  Release image
                image_result.Release()

        except PySpin.SpinnakerException as ex:
            # TODO check correct error handling
            raise ValueError(ex)

        # TODO: Make a note to remember we're using uvc timestamp
        timestamp = uvc_timestamp

        return frame.GetNDArray(), timestamp
