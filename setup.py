from setuptools import setup, find_packages
from distutils.util import convert_path

requirements = [
    "numpy",
    "pandas",
    "xarray",
    "scipy",
    "msgpack<1.0",
    "opencv-python",
]

main_ns = {}
ver_path = convert_path("pupil_recording_interface/_version.py")
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

setup(
    name="pupil_recording_interface",
    version=main_ns["__version__"],
    packages=find_packages(),
    long_description=open("README.rst").read(),
    entry_points={
        "console_scripts": ["pri = pupil_recording_interface:_run_cli"]
    },
    install_requires=requirements,
    include_package_data=True,
)
