""""""


class GazeAssessment(object):
    """ Base class for all recorders. """

    def __init__(self, folder):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        """
        self.folder = folder
    def plot_fps(self, camera = 'world'):
        import numpy as np
        import matplotlib.pyplot as plt

        #f = np.load("/home/kamran/recordings/flir_test/170/t265_timestamps.npy")
        f = np.load(self.folder + "/" + camera +"_timestamps.npy")
        f = np.diff(f)
        f = f[f!=0]

        fig, axes = plt.subplots(nrows = 2, ncols = 1, figsize = (12,12))

        axes[0].plot(range(len(f)),1/f, 'ob', markersize = 4, alpha = 0.4)
        axes[0].set_title('FPS Vs. Time', fontsize = 14)
        axes[0].yaxis.grid(True)
        axes[0].xaxis.grid(True)
        axes[0].set_xlabel('# of frames', fontsize = 12)
        axes[0].set_ylabel('FPS', fontsize = 14)


        axes[1].hist(1/f, 100, facecolor = 'g', edgecolor = 'k', linewidth = 1)
        axes[1].set_title('FPS histogram', fontsize = 14)
        axes[1].yaxis.grid(True)
        axes[1].xaxis.grid(True)
        axes[1].set_xlabel('FPS', fontsize = 12)
        axes[1].set_ylabel('count', fontsize = 14)

        fig.suptitle(camera, fontsize = 18)
        #plt.savefig(fname.replace('.hdf','_fps_'+str(fps)+'.png'), dpi=150)
        plt.show()

    def plot_gaze_accuracy(self, markerPosition, gazeDataFrame, gazeIndex):

        import pandas as pd
        import numpy as np
        import os
        import matplotlib.pyplot as plt
        import cv2
        from matplotlib import cm
        
        horizontal_pixels = 1280
        vertical_pixels = 1024
        horizontal_FOV = 92.5
        vertical_FOV = 70.8

        ratio_x = horizontal_FOV/horizontal_pixels
        ratio_y = vertical_FOV/vertical_pixels

        def rmse(predictions, targets):
            return np.sqrt(((predictions - targets) ** 2).mean())

        def pixels_to_angle_x(array):
            return (array - horizontal_pixels/2) * ratio_x

        def pixels_to_angle_y(array):
            return (array - vertical_pixels/2) * ratio_y


        gaze_norm_x = gazeDataFrame.iloc[gazeIndex].norm_pos_x.values
        gaze_norm_y = gazeDataFrame.iloc[gazeIndex].norm_pos_y.values

        gaze_pixel_x = gaze_norm_x * horizontal_pixels
        gaze_pixel_y = gaze_norm_y * vertical_pixels

        print('gazeX shape = ', gaze_pixel_x.shape)
        print('gazeY shape = ',gaze_pixel_y.shape)
        #print(np.array([gaze_pixel_x, gaze_pixel_y]).shape)
        gaze_homogeneous = cv2.convertPointsToHomogeneous(np.array([gaze_pixel_x, gaze_pixel_y]).T)
        gaze_homogeneous = np.squeeze(gaze_homogeneous)

        gaze_homogeneous[:,0] = pixels_to_angle_x(gaze_homogeneous[:,0])
        gaze_homogeneous[:,1] = pixels_to_angle_y(gaze_homogeneous[:,1])

        # This is important because the gaze values should be inverted in y direction
        gaze_homogeneous[:,1] = -gaze_homogeneous[:,1]

        print('gaze homogeneous shape =',gaze_homogeneous.shape)

        #print('gaze homogeneous =',gaze_homogeneous[0:5,:])

        marker_homogeneous = cv2.convertPointsToHomogeneous(markerPosition)
        marker_homogeneous = np.squeeze(marker_homogeneous)

        marker_homogeneous[:,0] = pixels_to_angle_x(marker_homogeneous[:,0])
        marker_homogeneous[:,1] = pixels_to_angle_y(marker_homogeneous[:,1])
        print('marker homogeneous shape =',marker_homogeneous.shape)
        #print('marker homogeneous =',marker_homogeneous[0:5,:])


        rmse_x = rmse(marker_homogeneous[:,0], gaze_homogeneous[:,0])
        rmse_y = rmse(marker_homogeneous[:,1], gaze_homogeneous[:,1])
        print('RMSE_az = ', rmse_x)
        print('RMSE_el = ', rmse_y)

        azimuthRange = 45
        elevationRange = 45
        fig = plt.figure(figsize = (10,10))
        plt.plot(marker_homogeneous[:,0], marker_homogeneous[:,1], 'or', markersize = 8, alpha = 0.6, label = 'marker')
        plt.plot(gaze_homogeneous[:,0], gaze_homogeneous[:,1], '+b', markersize = 8, alpha = 0.6, label = 'gaze')
        plt.title('Marker Vs. Gaze Positions (Raw)', fontsize = 18)
        plt.legend(fontsize = 12)
        plt.text(-40,40, ('RMSE_az = %.2f'%(rmse_x)), fontsize = 14)
        plt.text(-40,35, ('RMSE_el = %.2f'%(rmse_y)), fontsize = 14)
        #plt.text(-40,30, ('Distance = %d [inch] %d [cm]'%(depth_inch[depthIndex], depth_cm[depthIndex])), fontsize = 14)
        plt.xlabel('azimuth (degree)', fontsize = 14)
        plt.ylabel('elevation (degree)', fontsize = 14)
        plt.xticks(np.arange(-azimuthRange, azimuthRange + 1,5), fontsize = 14)
        plt.yticks(np.arange(-elevationRange, elevationRange + 1,5), fontsize = 14)
        plt.xlim((-azimuthRange, elevationRange))
        plt.ylim((-azimuthRange, elevationRange))
        plt.grid(True)

        #plt.savefig(dataPath + '/offline_data/gaze_accuracy_'+str(start_seconds)+'_'+ str(end_seconds)+'.png', dpi = 200 )
        plt.show()

    def calibration_assessment(self, folder):
        import pandas as pd
        import numpy as np
        import os
        import matplotlib.pyplot as plt
        import cv2
        from matplotlib import cm
        print("\n\nCalibration Assessment!")
        dataPath = '/hdd01/data_base_local/341/'
        print('dataPath [dummy]: ', dataPath)
        # TODO: For now I'm using a dummy folder
        # dataPath = folder
        # print('dataPath: ', dataPath)


        listOfImages = []
        markerFrames = []


        # termination criteria
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
        objp = np.zeros((8*6,3), np.float32)
        objp[:,:2] = np.mgrid[0:8,0:6].T.reshape(-1,2)

        # Arrays to store object points and image points from all the images.
        objpoints = [] # 3d point in real world space
        imgpoints = [] # 2d points in image plane.

        #images = glob.glob('*.jpg')

        cap = cv2.VideoCapture(dataPath + 'world.mp4')
        numberOfFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print( 'Total Number of Frames: ', numberOfFrames )
        #count = 1800
        #while(cap.isOpened()):

        fps = 30
        safeMargin = 2
        start_seconds = 70
        end_seconds = 120

        startIndex = (start_seconds + safeMargin) * fps
        endIndex = (end_seconds - safeMargin) * fps
        print('First Frame = %d'%(startIndex))
        print('Last Frame = %d'%(endIndex))

        scale_x = 0.5
        scale_y = 0.5
        print('scale[x,y] = ', scale_x, scale_y)

        myString = '-'
        for count in range(0, numberOfFrames):
            
            print("Progress: {0:.1f}% {s}".format(count*100/numberOfFrames, s = myString), end="\r", flush=True)
            if count < startIndex:
                ret, frame = cap.read()
                continue
            elif count > endIndex:
                break
            else:


                #Read the next frame from the video. If you set frame 749 above then the code will return the last frame.
                ret, img = cap.read()

                gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

                gray = cv2.resize(gray,None,fx=scale_x,fy=scale_y)
                # Find the chess board corners
                ret, corners = cv2.findChessboardCorners(gray, (6,8),None)

                # If found, add object points, image points (after refining them)
                if ret == True:
                    #print('====> Found [%d]!' %(count))
                    objpoints.append(objp)
                    

                    corners2 = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)


                    # Draw and display the corners
                    img_1 = cv2.drawChessboardCorners(cv2.resize(img,None,fx=scale_x,fy=scale_y), (6,8), corners2,ret)
                    cv2.imshow('Frame',img_1)
                    if cv2.waitKey(5) & 0xFF == ord('q'):
                        break

                    corners2 = np.squeeze(corners2)
                    #print('before : ', corners)
                    corners2[:,0] = corners2[:,0]*(1/scale_x)
                    corners2[:,1] = corners2[:,1]*(1/scale_y)
                    #print('after : ', corners)

                    imgpoints.append(corners2)
                    listOfImages.append(img_1)
                    markerFrames.append(count)
                    myString = '1'
                else:
                    myString = '0'
                    #cv2.imshow('img',gray)
                    #if cv2.waitKey(5) & 0xFF == ord('q'):
                    #    break
        print('\nDone!')
        cv2.destroyAllWindows()
        corners_pixels = np.array(imgpoints)
        corners_pixels.shape
        markerPosition = np.mean(corners_pixels, axis = 1)
        markerPosition.shape
        #np.save(dataPath + '/offline_data/markerPosition_'+str(start_seconds)+'_'+ str(end_seconds)+'.npy', markerPosition)
        #np.save(dataPath + '/offline_data/corners_pixel_'+str(start_seconds)+'_'+ str(end_seconds)+'.npy', corners_pixels)

        worldTimeStamps = np.load(dataPath + 'world_timestamps.npy')
        gazeDataFrame = pd.read_csv(dataPath + 'exports/000/gaze_positions.csv')

        gazeIndex = []
        for markerIndex in markerFrames:
            i = np.argmin(np.abs((gazeDataFrame.gaze_timestamp.values - worldTimeStamps[markerIndex]).astype(float)))
            gazeIndex.append(i)
        self.plot_gaze_accuracy(markerPosition, gazeDataFrame, gazeIndex)
        self.plot_fps('world')
        self.plot_fps('eye0')
