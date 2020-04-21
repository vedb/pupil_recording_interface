""""""


class GPoolDummy:
    """ Dummy for g_pool. """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
