from setuptools import setup, find_packages

requirements = [
    "numpy",
    "pandas",
    "xarray",
    "scipy",
    "msgpack<1.0",
    # TODO figure out conda dev setup and add "opencv-python",
]

setup(
    name="pupil_recording_interface",
    version="0.4.0",
    packages=find_packages(),
    long_description=open("README.rst").read(),
    install_requires=requirements,
    extras_require={"cv": ["opencv-python"]},  # TODO remove (see above)
    include_package_data=True,
)
