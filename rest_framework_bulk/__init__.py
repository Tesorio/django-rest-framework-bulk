__version__ = '1.0.0'
__author__ = 'Miroslav Shubernetskiy'

try:
    from .generics import *  # noqa
    from .mixins import *  # noqa
    from .serializers import *  # noqa
except Exception:
    pass
