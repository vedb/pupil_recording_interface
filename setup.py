from setuptools import setup, find_packages
import re

requirements = [
    "numpy",
    "pandas",
    "xarray",
    "scipy",
    "msgpack<1.0",
    "opencv-python",
]

# parse version number
with open("pupil_recording_interface/_version.py", "rt") as f:
    mo = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)

if mo:
    version = mo.group(1)
else:
    raise RuntimeError("Unable to find version string.")

setup(
    name="pupil_recording_interface",
    version=version,
    packages=find_packages(),
    long_description=open("README.rst").read(),
    entry_points={
        "console_scripts": ["pri = pupil_recording_interface.legacy:_run_cli"]
    },
    install_requires=requirements,
    include_package_data=True,
)
