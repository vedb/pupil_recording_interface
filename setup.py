from setuptools import setup, find_packages

requirements = [
    "numpy",
    "pandas",
    "xarray",
    "scipy",
    "opencv-python",
    "msgpack<1.0",
]

setup(
    name="pupil_recording_interface",
    version="0.3.0",
    packages=find_packages(),
    long_description=open("README.rst").read(),
    install_requires=requirements,
    include_package_data=True,
)
