__version__ = '0.0.1'

from .core import dispatch
from .core import metadispatch
from .core import create_default_metadispatcher

from . import types
from .types import Dispatcher
from .types import NextDispatch
