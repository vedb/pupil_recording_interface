from setuptools import setup, find_packages

requirements = [
    "numpy",
    "pandas",
    "xarray",
    "scipy",
    "msgpack<1.0",
]

setup(
    name="pupil_recording_interface",
    version="0.0.2",
    packages=find_packages(),
    long_description=open("README.rst").read(),
    install_requires=requirements,
    include_package_data=True,
)
