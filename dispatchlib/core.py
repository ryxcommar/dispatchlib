import inspect
import importlib
import os
import sys

from typing import Any
from typing import Callable
from typing import ForwardRef
from typing import Union
from typing import Tuple
from typing import Optional
from typing import _GenericAlias
from functools import update_wrapper

from sortedcontainers import SortedKeyList
from typeguard import check_type

from .types import NextDispatch
from .types import FunctionMixin
from .types import Dispatcher
from .types import DispatchedCallable


def _determine_priority(registry: SortedKeyList, priority: int):
    if priority is not None:
        return priority
    try:
        max_prio = max(f.priority for f in registry if f.priority < sys.maxsize)
    except ValueError:
        max_prio = -1
    return max_prio + 1


def metadispatch(base_func: Optional[callable] = None):
    """This is a GenericFunction class without 'smart' registration. Why does
    this exist? Because the registration logic itself is a generic function! So
    we need a way to define a generic function that doesn't use the smart
    registration.
    """

    registry = SortedKeyList(key=lambda f: f.priority)

    def dynamic_dispatcher(*args, **kwargs):
        """Dispatch the registered functions."""
        nonlocal registry
        for f in registry:
            try:
                if f.validate(args[0]):
                    _kwargs = kwargs.copy()
                    if '_globals' not in inspect.signature(f).parameters:
                        _kwargs.pop('_globals', None)
                    res = f(*args, **_kwargs)
                    return res
            except NextDispatch:
                continue

    # let automatic typechecking in pycharm do its job
    dynamic_dispatcher: Dispatcher

    def register(
            check_func: Callable[[Any], bool],
            priority: int = None
    ):
        """Unlike the actual GenericFunction class, this one only supports
        functions for checking, not other types.
        """
        nonlocal registry
        def _wrap(func: callable):
            if isinstance(func, FunctionMixin):
                func = func.func
            new_func = DispatchedCallable(
                func=func,
                validate=check_func,
                priority=_determine_priority(registry, priority)
            )
            registry.add(new_func)
            return func
        return _wrap

    if base_func is None:
        def base_func(checked_input: Any, *args, **kwargs):
            raise TypeError('Valid implementation not found')
        base_func.__name__ = '<dispatchlib.metadispatch>'

    dynamic_dispatcher.register = register
    dynamic_dispatcher.registry = registry
    update_wrapper(dynamic_dispatcher, base_func)
    return dynamic_dispatcher


def create_default_metadispatcher(func: callable = None):
    f = metadispatch(func)

    @f.register(lambda c: isinstance(c, type),
                priority=100)
    def create_checker_type(val):
        """Check against a single type."""
        def checker(x):
            return isinstance(x, val)
        return checker

    @f.register(lambda val: isinstance(val, _GenericAlias),
                priority=101)
    def create_checker_generic_alias(val):
        """Check against a single type."""
        def checker(x):
            try:
                check_type('check', x, val)
            except TypeError:
                return False
            else:
                return True
        return checker

    # This func assumes strings are representations of Python objects.
    @f.register(lambda val: isinstance(val, str),
                priority=102)
    def create_checker_forward_ref(val, _globals: dict = None):
        """Lazy load type, then check against it (attempt 1)."""
        _globals = _globals or {}
        try:
            target_type = ForwardRef(val)._evaluate(_globals, {})
            def checker(x):
                return isinstance(x, target_type)
            return checker
        except NameError:
            raise NextDispatch

    @f.register(lambda val: isinstance(val, str),
                priority=103)
    def create_checker_import_via_str(val):
        """Lazy load type, then check against it (attempt 2)."""
        def checker(x):
            modname, typename = os.path.splitext(val)
            packagename = modname.split('.')[0]
            if repr(type(x)).find(packagename) == -1:
                # Avoid unnecessary imports
                return False
            mod = importlib.import_module(modname)
            target_type = getattr(mod, typename[1:])
            return isinstance(x, target_type)
        return checker

    @f.register(lambda val: callable(val),
                priority=104)
    def create_checker_generic_callable(val):
        """Return the callable as-is."""
        return val

    return f


_default_metadispatcher = create_default_metadispatcher()


def dispatch(
        *func: Tuple[Optional[callable]],
        metadispatcher: Dispatcher = None,
):
    if metadispatcher is None:
        metadispatcher = _default_metadispatcher

    if len(func) == 0:
        return lambda f: dispatch(f, metadispatcher=metadispatcher)
    elif len(func) > 1:
        raise TypeError(
            f'dispatch() takes 1 positional argument but {len(func)} were given'
        )

    if func[0] is None:
        def base_func(checked_input: Any, *args, **kwargs):
            raise TypeError('Valid implementation not found')
        base_func.__name__ = '<dispatchlib.dispatch>'
    else:
        base_func: callable = func[0]

    registry = SortedKeyList(key=lambda f: f.priority)

    def register(
            check: Union[type, str, Callable[[Any], bool]] = None,
            priority: int = None
    ):
        nonlocal registry
        nonlocal metadispatcher

        def _wrap(func: callable):
            nonlocal check
            if isinstance(func, DispatchedCallable):
                func = func.func
            if check is None:
                check = list(inspect.signature(func).parameters.values())[0].annotation
                if check is inspect._empty:
                    raise TypeError(
                        'You need to either register a type, or have a type '
                        'annotation in the first arg of the decorated '
                        'function.'
                    )
            new_func = DispatchedCallable(
                func=func,
                validate=metadispatcher(check,
                                        _globals=func.__globals__),
                priority=_determine_priority(registry, priority)
            )
            registry.add(new_func)
            return func

        return _wrap

    def dynamic_dispatcher(*args, **kwargs):
        """Dispatch the registered functions."""
        nonlocal registry
        for f in registry:
            try:
                if f.validate(args[0]):
                    res = f(*args, **kwargs)
                    return res
            except NextDispatch:
                continue

    dynamic_dispatcher: Dispatcher
    dynamic_dispatcher.register = register
    dynamic_dispatcher.registry = registry

    dynamic_dispatcher.register(lambda x: True, priority=sys.maxsize)(base_func)
    update_wrapper(dynamic_dispatcher, base_func)

    return dynamic_dispatcher
