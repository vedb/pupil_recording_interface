from pupil_recording_interface import \
    VideoConfig, VideoRecorder, MultiStreamRecorder
from pupil_recording_interface.config import OdometryConfig
import yaml
import sys

if __name__ == '__main__':

    with open("/home/kamran/Code/pupil_recording_interface/data_collection.yml") as f:
        config_file = yaml.load(f, Loader = yaml.FullLoader)

    print('Data Collection Settings: \n')
    for k in config_file['Experiment'].keys():
        print(k, ' : ', config_file['Experiment'][k])
    print('\n')

    # recording folder
    #folder = '~/recordings/flir_test'
    folder = config_file['Experiment']['recording_directory']

    with open("/home/kamran/Code/pupil_recording_interface/data_collection.yml") as f:
        config_file = yaml.load(f, Loader = yaml.FullLoader)

    world_camera_id = input("\n Which World Camera? ...\n Please enter 0 for FLIR or 1 for Pupil: ")
    print
    if world_camera_id == '0':
        print("FLIR World Camera Selected\n")
    elif world_camera_id == '1':
        print("Pupil World Camera Selected\n")
    else:
        print("Undefined World Camera! Terminate\n", world_camera_id)
        sys.exit(0)


    print('\nSystem Settings:')
    for k in config_file['System'].keys():
        print(k, ' : ', config_file['System'][k])
    print('\n')

    configs = []
    for k in config_file['System'].keys():
        if ('camera' in k):
            if ('world' in k and k != "world_camera_" + str(world_camera_id) ):
                continue
            configs.append(VideoConfig( 
            device_type = config_file['System'][k]['device_type'],
            device_uid = config_file['System'][k]['device_uid'], 
            name = config_file['System'][k]['name'],
            resolution = eval(config_file['System'][k]['resolution']),
            fps = config_file['System'][k]['fps'],
            codec=config_file['System'][k]['codec']))
            #exposure_value=exposure_value, gain=gain),
        elif ('odometry' in k):
            configs.append(OdometryConfig(
            device_type = config_file['System'][k]['device_type'],
            device_uid = config_file['System'][k]['device_uid'], 
            name = config_file['System'][k]['name']))
        else:
            print('Invalid device was found in yaml file!')
    

    # change this to False for multi-threaded recording
    single_threaded = False

    if single_threaded:
        recorder = VideoRecorder.from_config(
            configs[0], folder, overwrite=True)
        recorder.show_video = False
    else:
        recorder = MultiStreamRecorder(folder, configs, show_video=False, data_collection_config = config_file)
    recorder.run()