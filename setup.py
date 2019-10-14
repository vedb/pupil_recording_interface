from setuptools import setup, find_packages

requirements = ['numpy', 'pandas', 'xarray', 'scipy', 'msgpack', 'opencv']

setup(
    name='pupil_recording_interface',
    version='0.0.1',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=requirements,
)
