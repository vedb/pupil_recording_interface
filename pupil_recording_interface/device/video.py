""""""
import abc

import cv2
# TODO import uvc here

from pupil_recording_interface.device import BaseDevice
import PySpin
from datetime import datetime
import time
import statistics

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

        self.previous_timestamp = 0
        self.current_timestamp = 0

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
        #print('FLIR Frame: ', frame)
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
        self.previous_timestamp = self.current_timestamp
        self.current_timestamp = time.time()

        start = time.time()
        if mode not in ('img', 'bgr', 'gray', 'jpeg_buffer'):
            raise ValueError('Unsupported mode: {}'.format(mode))
       
        uvc_frame = self.capture.get_frame()

        end = time.time()
        #print('T = ', end - start)
        # print( ' (UVC)=> call_back: {:.3f} capture_time: {:.3f}'.format(\
        #    1/(self.current_timestamp - self.previous_timestamp),\
        #    1/(end - self.current_timestamp)))

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


class  VideoDeviceFLIR(BaseVideoDevice):
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
        self.flir_camera = None
        self.flir_nodemap = None
        self.flire_system = None
        self.timestamp_offsets = 0

    def _compute_timestamp_offset(self, cam, number_of_iterations, camera_type):
        """ Gets timestamp offset in seconds from input camera """

        # This method is required because the timestamp stored in the camera is relative to when it was powered on, so an
        # offset needs to be applied to get it into epoch time; from tests I've done, this appears to be accurate to ~1e-3
        # seconds.
        print("Measuring TimeStamp Offset ...")
        timestamp_offsets = []
        for i in range(number_of_iterations):
            # Latch timestamp. This basically "freezes" the current camera timer into a variable that can be read with
            # TimestampLatchValue()
            cam.TimestampLatch.Execute()

            # Compute timestamp offset in seconds; note that timestamp latch value is in nanoseconds
            
            if(camera_type == 'BlackFly'):
                timestamp_offset = datetime.now().timestamp() - cam.TimestampLatchValue.GetValue()/1e9
            elif(camera_type == 'Chameleon'):
                timestamp_offset = datetime.now().timestamp() - cam.Timestamp.GetValue()/1e9
            else:
                print('\n\nInvalid Camera Type!!\n\n')
                return 0

            # Append
            timestamp_offsets.append(timestamp_offset)

        # Return the median value
        return statistics.median(timestamp_offsets)


    #@classmethod
    def print_device_info(self, nodemap):
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

    #@classmethod    
    def _get_capture(self, uid, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """
        # TODO specify additional keyword arguments
        import PySpin
        from datetime import datetime

        system = PySpin.System.GetInstance()
        self.flire_system = system

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
        self.flir_camera = capture
        print('FLIR Camera : ', capture)

        # Initialize camera
        capture.Init()

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = capture.GetTLDeviceNodeMap()
        nodemap_tlstream = capture.GetTLStreamNodeMap()
        self.print_device_info(nodemap_tldevice)

        capture.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        
        
        # Retrieve GenICam nodemap
        nodemap = capture.GetNodeMap()
        self.nodemap = nodemap

        device_model = PySpin.CStringPtr(nodemap.GetNode("DeviceModelName")).GetValue()
        
        if ('Chameleon' in device_model):
            self.camera_type = 'Chameleon'
        elif('Blackfly' in device_model):
            self.camera_type = 'BlackFly'
        else:
            self.camera_type = device_model
            print('\n\nInvalid Camera Type during initit_1!!\n\n')

        print('FLIR Camera Type = ', self.camera_type)
        #Todo: Read device type from camera
        #self.camera_type = 'Chameleon'
        if(self.camera_type == 'Chameleon'):
            print("Initializing Chameleon ...")
            node_AcquisitionFrameRateAuto = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionFrameRateAuto"))
            node_AcquisitionFrameRateAuto_off = node_AcquisitionFrameRateAuto.GetEntryByName("Off")
            node_AcquisitionFrameRateAuto.SetIntValue(node_AcquisitionFrameRateAuto_off.GetValue())


            node_AcquisitionFrameRateEnable_bool = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnabled"))
            node_AcquisitionFrameRateEnable_bool.SetValue(True) 

            node_AcquisitionFrameRate = PySpin.CFloatPtr(nodemap.GetNode("AcquisitionFrameRate"))
            node_AcquisitionFrameRate.SetValue(self.fps)
        elif(self.camera_type == 'BlackFly'):
            print("Initializing BlackFly ...")
            #node_AcquisitionFrameRateEnable_bool = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnable"))
            #node_AcquisitionFrameRateEnable_bool.SetValue(True) 
            capture.AcquisitionFrameRateEnable.SetValue(True)
            capture.AcquisitionFrameRate.SetValue(self.fps)
        else:
            print('\n\nInvalid Camera Type during initit_2!!\n\n')

        print('Set FLIR fps to:', self.fps)


        StreamBufferHandlingMode = PySpin.CEnumerationPtr(
            nodemap_tlstream.GetNode('StreamBufferHandlingMode'))
        StreamBufferHandlingMode_Entry = StreamBufferHandlingMode.GetEntryByName(
            'NewestOnly')
        StreamBufferHandlingMode.SetIntValue(StreamBufferHandlingMode_Entry.GetValue())
        print('Set FLIR buffer handling to: NewestOnly: ', StreamBufferHandlingMode_Entry.GetValue())

        # TODO: Find an equivalent way of reading the actual frame rate for Chameleon
        # Chameleon doesn't have this register or anything similar to this
        if (self.camera_type == 'BlackFly'):
            print('Actual Frame Rate = ', capture.AcquisitionResultingFrameRate.GetValue())

        #multi_pyspin.node_cmd(serial, 'TLStream.StreamBufferHandlingMode', 'SetValue', 'RW', 'PySpin.StreamBufferHandlingMode_OldestFirst')
        
        # Set acquisition mode to continuous
        '''
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) \
                or not PySpin.IsWritable(node_acquisition_mode):
            raise ValueError(
                'Unable to set acquisition mode to continuous (enum '
                'retrieval).')

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = \
            node_acquisition_mode.GetEntryByName('Continuous')#'SingleFrame'
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) \
                or not PySpin.IsReadable(node_acquisition_mode_continuous):
            raise ValueError(
                'Unable to set acquisition mode to continuous (entry '
                'retrieval).')
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
        '''

        self.timestamp_offset = self._compute_timestamp_offset(capture, 20, self.camera_type)
        print("\nTimeStamp Offset = ", self.timestamp_offset/1e9)

        #  Begin acquiring images
        capture.BeginAcquisition()
        print('Acquisition Started!')

        return capture

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        # TODO return grayscale frame if mode=='gray'
        #import PySpin
        #from datetime import datetime
        self.previous_timestamp = self.current_timestamp
        self.current_timestamp = time.time()
        #  Begin acquiring images
        #self.capture.BeginAcquisition()

        
        try:
            #  Retrieve next received image
            image_result = self.capture.GetNextImage()
            self.capture.TimestampLatch.Execute()

            #  Ensure image completion
            if image_result.IsIncomplete():
                # TODO check if this is a valid way of handling an
                #  incomplete image
                print('\n\nImage Incomplete!')
                return self._get_frame_and_timestamp(mode)

            else:
                # TODO convert to correct color format
                frame = image_result.Convert(
                    PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)

                #  Release image
                image_result.Release()

            # TODO: Image Pointer doesn't have any GetTimeStamp() attribute
            #timestamp = float(image_result.GetTimestamp()) / 1e9
            # TODO: Temporary solution to fix the FLIR timestamp issue
            if(self.camera_type == 'BlackFly'):
                timestamp = self.timestamp_offset + self.capture.TimestampLatchValue.GetValue()/1e9
            elif(self.camera_type == 'Chameleon'):
                timestamp = self.timestamp_offset + self.capture.Timestamp.GetValue()/1e9
            else:
                print('\n\nInvalid Camera Type during get_frame!!\n\n')
            #now = datetime.now()
            #timestamp = float(datetime.timestamp(now)) / 1e9

        except PySpin.SpinnakerException as ex:
            # TODO check correct error handling
            raise ValueError(ex)
        #self.capture.EndAcquisition()
        end = time.time()
        #print('T = ', end - start)

        # print(' (FLIR)=> call_back: {:2.3f} capture_time: {:2.3f} read_fps: {:2.3f}'.format(\
        #     1/(self.current_timestamp - self.previous_timestamp),\
        #     1/(end - self.current_timestamp), self.capture.AcquisitionResultingFrameRate.GetValue()))
        a = frame.GetNDArray()
        return a, timestamp
