from setuptools import setup, find_packages

requirements = [
    'numpy', 'pandas', 'xarray', 'scipy', 'msgpack', 'opencv-python']

setup(
    name='pupil_recording_interface',
    version='0.0.1',
    packages=find_packages(),
    long_description=open('README.rst').read(),
    entry_points={
        'console_scripts': ['pri = pupil_recording_interface:_run_cli']},
    install_requires=requirements,
    include_package_data=True,
)
