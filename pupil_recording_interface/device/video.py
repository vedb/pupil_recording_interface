""""""
import abc

import cv2
# TODO import uvc here

from pupil_recording_interface.device import BaseDevice


class BaseVideoDevice(BaseDevice):
    """ Base class for all video devices. """

    def __init__(self, uid, resolution, fps, **kwargs):
        """ Constructor.

        Parameters
        ----------
        uid: str
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
        super(BaseVideoDevice, self).__init__(uid)

        self.resolution = resolution
        self.fps = fps

        self.capture = None
        self.capture_kwargs = kwargs

    @property
    def is_started(self):
        return self.capture is not None

    @classmethod
    @abc.abstractmethod
    def _get_capture(cls, device_name, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """

    @abc.abstractmethod
    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """

    def show_frame(self, frame):
        """ Show a frame through OpenCV's imshow.

        Parameters
        ----------
        frame : array_like
            The frame to display.
        """
        # TODO move this to BaseVideoRecorder?
        cv2.imshow(self.uid, frame)
        return cv2.waitKey(1)

    def start(self):
        """ Start this device. """
        # TODO for some devices, capture has to be initialized here for
        #  multi-threaded operation, check if we can circumvent this
        if not self.is_started:
            self.capture = self._get_capture(
                self.uid, self.resolution, self.fps, **self.capture_kwargs)

    def stop(self):
        """ Stop this device. """
        self.capture = None


class VideoDeviceUVC(BaseVideoDevice):
    """ UVC video device. """

    @classmethod
    def _get_connected_device_uids(cls):
        """ Get a mapping from devices names to UIDs. """
        import uvc
        return {
            device['name']: device['uid'] for device in uvc.device_list()}

    @classmethod
    def _get_uvc_device_uid(cls, device_name):
        """ Get the UID for a UVC device by name. """
        try:
            return cls._get_connected_device_uids()[device_name]
        except KeyError:
            raise ValueError(
                'Device with name {} not connected.'.format(device_name))

    @classmethod
    def _get_available_modes(cls, device_uid):
        """ Get the available modes for a device by UID. """
        import uvc
        return uvc.Capture(device_uid).avaible_modes  # [sic]

    @classmethod
    def _get_controls(cls, device_uid):
        """ Get the current controls for a device by UID. """
        import uvc
        return {
            c.display_name: c.value for c in uvc.Capture(device_uid).controls}

    @classmethod
    def _get_capture(cls, uid, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """
        device_uid = cls._get_uvc_device_uid(uid)

        # verify selected mode
        if resolution + (fps,) not in cls._get_available_modes(device_uid):
            raise ValueError('Unsupported frame mode: {}x{}@{}fps.'.format(
                resolution[0], resolution[1], fps))

        import uvc
        capture = uvc.Capture(device_uid)
        capture.frame_mode = resolution + (fps,)

        return capture

    @classmethod
    def _get_timestamp(cls):
        """ Get the current monotonic time from the UVC backend. """
        import uvc
        return uvc.get_time_monotonic()

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        if mode not in ('img', 'bgr', 'gray', 'jpeg_buffer'):
            raise ValueError('Unsupported mode: {}'.format(mode))

        uvc_frame = self.capture.get_frame()

        return getattr(uvc_frame, mode), uvc_frame.timestamp

    @property
    def uvc_device_uid(self):
        """ The UID of the UVC device. """
        return self._get_uvc_device_uid(self.uid)

    @property
    def available_modes(self):
        """ Available frame modes for this device. """
        if self.capture is None:
            return self._get_available_modes(self.uvc_device_uid)
        else:
            return self.capture.avaible_modes  # [sic]

    @property
    def controls(self):
        """ Current controls for this device. """
        if self.capture is None:
            return self._get_controls(self.uvc_device_uid)
        else:
            return {c.display_name: c.value for c in self.capture.controls}

    def get_uvc_frame(self):
        """ Grab a uvc.Frame from the device.

        Returns
        -------
        uvc.Frame:
            The captured frame.
        """
        return self.capture.get_frame()


class VideoDeviceFLIR(BaseVideoDevice):
    """ FLIR video device. """

    def __init__(self, uid, resolution, fps, **kwargs):
        """ Constructor.

        Parameters
        ----------
        uid: str
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
        super(VideoDeviceFLIR, self).__init__(uid, resolution, fps, **kwargs)

    @classmethod
    def print_device_info(cls, nodemap):
        """
        This function prints the device information of the camera from the
        transport layer; please see NodeMapInfo example for more in-depth
        comments on printing device information from the nodemap.
        """
        import PySpin

        print('*** DEVICE INFORMATION ***\n')

        try:
            node_device_information = PySpin.CCategoryPtr(
                nodemap.GetNode('DeviceInformation'))

            if PySpin.IsAvailable(node_device_information) \
                    and PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = PySpin.CValuePtr(feature)
                    print('%s: %s' % (
                        node_feature.GetName(), node_feature.ToString()
                        if PySpin.IsReadable(node_feature)
                        else 'Node not readable'))

            else:
                print('Device control information not available.')

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

    @classmethod
    def _get_capture(cls, uid, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """
        # TODO specify additional keyword arguments
        import PySpin

        system = PySpin.System.GetInstance()

        # Retrieve list of cameras from the system
        cam_list = system.GetCameras()
        print('List of Cameras: ', cam_list)
        num_cameras = cam_list.GetSize()

        print('Number of cameras detected: %d' % num_cameras)

        # Finish if there are no cameras
        if num_cameras == 0:
            # Clear camera list before releasing system
            cam_list.Clear()

            # Release system instance
            system.ReleaseInstance()

            raise ValueError('Not enough cameras!')

        # TODO: Clean this up! There might be multiple Cameras?!!?
        capture = cam_list[0]
        print('FLIR Camera : ', capture)

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = capture.GetTLDeviceNodeMap()
        cls.print_device_info(nodemap_tldevice)

        # Initialize camera
        capture.Init()

        # Retrieve GenICam nodemap
        nodemap = capture.GetNodeMap()

        # Set acquisition mode to continuous
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) \
                or not PySpin.IsWritable(node_acquisition_mode):
            raise ValueError(
                'Unable to set acquisition mode to continuous (enum '
                'retrieval).')

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = \
            node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) \
                or not PySpin.IsReadable(node_acquisition_mode_continuous):
            raise ValueError(
                'Unable to set acquisition mode to continuous (entry '
                'retrieval).')

        #  Begin acquiring images
        capture.BeginAcquisition()
        print('Acquisition Started!')

        return capture

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        # TODO return grayscale frame if mode=='gray'
        import PySpin

        try:
            #  Retrieve next received image
            image_result = self.capture.GetNextImage()

            #  Ensure image completion
            if image_result.IsIncomplete():
                # TODO check if this is a valid way of handling an
                #  incomplete image
                return self._get_frame_and_timestamp(mode)

            else:
                # TODO convert to correct color format
                frame = image_result.Convert(
                    PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR)

                #  Release image
                image_result.Release()

            timestamp = float(image_result.GetTimestamp()) / 1e9

        except PySpin.SpinnakerException as ex:
            # TODO check correct error handling
            raise ValueError(ex)

        return frame, timestamp
