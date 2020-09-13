from typing import Any
from typing import Callable
from typing import Iterable


def _create_getter_and_setter(name: str):
    def getter(self):
        return getattr(self.func, name)
    getter.__name__ = name
    prop = property(getter)

    def setter(self, value):
        setattr(self.func, name, value)
    setter.__name__ = name
    prop = prop.setter(setter)

    return prop


class _PrioritySortable:
    priority: int

    def __init__(self, priority: int = 100):
        self.priority = priority

    def __lt__(self, other): return self.priority < other.priority
    def __le__(self, other): return self.priority <= other.priority
    def __gt__(self, other): return self.priority > other.priority
    def __ge__(self, other): return self.priority >= other.priority
    def __eq__(self, other): return self.priority == other.priority


class FunctionMixin(object):
    """Mixin for making classes look like functions.
    This class isn't too fancy: if you store random non-standard attributes
    inside your function then they are not directly accessible at the top-level
    of the the subclass. The attributes this mixin provides are pre-defined.
    """
    def __init__(self, func: callable):
        self.func = func

    for name in [
        '__annotations__',
        '__closure__',
        '__code__',
        '__defaults__',
        '__kwdefaults__',
        '__name__'
    ]:
        locals()[name] = _create_getter_and_setter(name)

    @property
    def __funcdoc__(self):
        return self.func.__doc__

    @__funcdoc__.setter
    def __funcdoc__(self, value):
        self.func.__doc__ = value

    @property
    def __globals__(self):
        return self.func.__globals__

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class NextDispatch(Exception):
    pass


class DispatcherType(type):
    def __instancecheck__(cls, instance):
        return (
            callable(instance)
            and hasattr(instance, 'register')
            and hasattr(instance, 'registry')
            and callable(instance.register)
            and hasattr(instance.registry, '__iter__')
        )


class Dispatcher(FunctionMixin, metaclass=DispatcherType):
    dispatch: callable
    register: callable
    registry: Iterable

    def __new__(cls, func: callable = None, metadispatcher: callable = None):
        from .core import dispatch
        return dispatch(func, metadispatcher=metadispatcher)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class MetaDispatcher(FunctionMixin, metaclass=DispatcherType):
    dispatch: callable
    register: callable
    registry: Iterable

    def __new__(cls, func: callable = None):
        from .core import metadispatch
        return metadispatch(func)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class DispatchedCallable(FunctionMixin, _PrioritySortable):

    def __init__(
            self,
            func: callable,
            validate: Callable[[Any], bool],
            priority: int = 100
    ):
        self.validate = validate
        FunctionMixin.__init__(self, func)
        _PrioritySortable.__init__(self, priority)

    def __repr__(self):
        content = ', '.join(
            f'{attr}={getattr(self, attr)!r}'
            for attr in ('func', 'validate', 'priority')
        )
        return f'{self.__class__.__name__}({content})'
