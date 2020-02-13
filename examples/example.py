from __future__ import print_function
import uvc
import logging
import cv2
import numpy as np

import os
import PySpin

NUM_IMAGES = 200  # number of images to grab


def acquire_images(cam, nodemap):
    global NUM_IMAGES
    """
    This function acquires 50 images from a device, stores them in a list, and returns the list.
    please see the Acquisition example for more in-depth comments on acquiring images.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :type cam: CameraPtr
    :type nodemap: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print("*** IMAGE ACQUISITION ***\n")
    try:
        fourcc = "XVID"
        size = (400, 400)
        eyeVideo_0 = cv2.VideoWriter(
            "captures/eye0.avi", cv2.VideoWriter_fourcc(*fourcc), 30, size
        )
        eyeVideo_1 = cv2.VideoWriter(
            "captures/eye1.avi", cv2.VideoWriter_fourcc(*fourcc), 30, size
        )
        worldVideo = cv2.VideoWriter(
            "captures/world.avi",
            cv2.VideoWriter_fourcc(*fourcc),
            60,
            (2048, 1536),
        )

        result = True

        # Set acquisition mode to continuous
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode("AcquisitionMode")
        )
        if not PySpin.IsAvailable(
            node_acquisition_mode
        ) or not PySpin.IsWritable(node_acquisition_mode):
            print(
                "Unable to set acquisition mode to continuous (enum retrieval). Aborting..."
            )
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(
            "Continuous"
        )
        if not PySpin.IsAvailable(
            node_acquisition_mode_continuous
        ) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print(
                "Unable to set acquisition mode to continuous (entry retrieval). Aborting..."
            )
            return False

        acquisition_mode_continuous = (
            node_acquisition_mode_continuous.GetValue()
        )

        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        print("Acquisition mode set to continuous...")

        #  Begin acquiring images
        cam.BeginAcquisition()

        print("Acquiring images...")

        # Retrieve, convert, and save images
        images = list()

        for i in range(NUM_IMAGES):
            try:

                frame_0 = cap_0.get_frame_robust()
                frame_1 = cap_1.get_frame_robust()
                print(frame_0.img.shape)
                # cv2.imwrite('captures/eye_'+str(i)+'.png',np.concatenate((frame_0.bgr, frame_1.bgr),axis=1))
                eyeVideo_0.write(frame_0.bgr)
                eyeVideo_1.write(frame_1.bgr)

                # cv2.imshow("img",np.concatenate((frame_0.bgr, frame_1.bgr),axis=1))#frame.gray
                # if(cv2.waitKey(1) & 0xFF == ord('q')):
                #    break

                #  Retrieve next received image
                image_result = cam.GetNextImage()

                #  Ensure image completion
                if image_result.IsIncomplete():
                    print(
                        "Image incomplete with image status %d..."
                        % image_result.GetImageStatus()
                    )

                else:
                    #  Print image information; height and width recorded in pixels
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    print(
                        "Grabbed Image %d, width = %d, height = %d"
                        % (i, width, height)
                    )

                    #  Convert image to mono 8 and append to list
                    images.append(
                        image_result.Convert(
                            PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR
                        )
                    )

                    worldFrame = image_result.Convert(
                        PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR
                    ).GetNDArray()
                    worldVideo.write(worldFrame)

                    #  Release image
                    image_result.Release()
                    print("")

            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex)
                result = False
        eyeVideo_0.release()
        eyeVideo_1.release()
        worldVideo.release()
        # End acquisition
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        result = False

    return result, images


def print_device_info(nodemap):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print("*** DEVICE INFORMATION ***\n")

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(
            nodemap.GetNode("DeviceInformation")
        )

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(
            node_device_information
        ):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print(
                    "%s: %s"
                    % (
                        node_feature.GetName(),
                        node_feature.ToString()
                        if PySpin.IsReadable(node_feature)
                        else "Node not readable",
                    )
                )

        else:
            print("Device control information not available.")

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return False

    return result


def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        result &= print_device_info(nodemap_tldevice)

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Acquire list of images
        err, images = acquire_images(cam, nodemap)
        if err < 0:
            return err

        # result &= save_list_to_avi(nodemap, nodemap_tldevice, images)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        result = False

    return result


def main():

    # TODO: This should be handled by the class not as a gloabl variable
    global cap_0, cap_1

    logging.basicConfig(level=logging.INFO)

    dev_list = uvc.device_list()
    # TODO: These device_ids need to be handleded better and independent of their order!
    device_id = 1
    cap_0 = uvc.Capture(dev_list[device_id]["uid"])
    print("device_properties:\n", dev_list[device_id])

    device_id = 2
    cap_1 = uvc.Capture(dev_list[device_id]["uid"])
    print("device_properties:\n", dev_list[device_id])
    cap_0.frame_mode = (400, 400, 30)
    cap_1.frame_mode = (400, 400, 30)

    # Uncomment the following lines to configure the Pupil 200Hz IR cameras:
    # controls_dict = dict([(c.display_name, c) for c in cap.controls])
    # controls_dict['Auto Exposure Mode'].value = 1
    # controls_dict['Gamma'].value = 200

    print("resolutions for Cam_0", cap_0.avaible_modes)
    print("resolutions for Cam_1", cap_1.avaible_modes)

    """
    Example entry point; please see Enumeration example for more in-depth
    comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # Since this application saves images in the current folder
    # we must ensure that we have permission to write to this folder.
    # If we do not have permission, fail right away.
    try:
        test_file = open("test.txt", "w+")
    except IOError:
        print(
            "Unable to write to current directory. Please check permissions."
        )
        input("Press Enter to exit...")
        return False

    test_file.close()
    os.remove(test_file.name)

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print(
        "Library version: %d.%d.%d.%d"
        % (version.major, version.minor, version.type, version.build)
    )

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print("Number of cameras detected: %d" % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print("Not enough cameras!")
        input("Done! Press Enter to exit...")
        return False

    # Run example on each camera
    for i, cam in enumerate(cam_list):

        print("Running example for camera %d..." % i)

        result &= run_single_camera(cam)
        print("Camera %d example complete... \n" % i)

    # Release reference to camera
    # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
    # cleaned up when going out of scope.
    # The usage of del is preferred to assigning the variable to None.
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input("Done! Press Enter to exit...")
    return result


if __name__ == "__main__":
    main()
