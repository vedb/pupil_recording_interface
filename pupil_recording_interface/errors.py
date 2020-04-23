""""""


class DeviceNotConnected(RuntimeError):
    """ Raised when the requested device is not connected. """


class IllegalSetting(ValueError):
    """ Raised when the device does not support the requested setting. """
