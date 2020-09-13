# Dispatchlib

Dispatchlib is a metaprogramming library for creating single-dispatched generic functions, similar to `functools.singledispatch`, with a few additional goodies:

- Supports type annotations that utilize Python's builtin `typing` module.
- Lazy-loads string annotations (i.e. types declared via string).
- Priority dispatching: you can set the "priority" of an overloaded implementation. Basically `dispatchlib.dispatch` is a big ol `if elif elif` factory, and the order is determined by `@f.register(priority=?)`
- A "`metadispatch`" that lets you overload the dispatcher itself. (Hard to explain; see example for clarification.)

Dispatchlib's `dispatch` decorator is not a strict superset of `functools.singledispatch`. There are a few things in `functools.singledispatch` that are not in `single`:

- `dispatchlib.dispatch` requires that you always call the register decorator like this: `@f.regsiter()` whereas `functools.singledispatch`. The reason why is because `dispatchlib.dispatch` can dispatch not just based on types but also based on functions , so the first arg in the `register` decorator being a function is not sufficient to conclude whether it's being called or not prior to decoration.
- `functools.singledispatch` supports dynamic polymorphism using `__mro__`, whereas `dispatchlib.dispatch` dispatches based on running a check for each overloaded implementation; by default, checks are run in FIFO order, with the exception of the "base" function, which is always run last.
- `functools.singledispatch` is faster.

## Install

```shell
pip install dispatchlib
```

## Examples

### Basic Example 1

```python
from dispatchlib import dispatch
from typing import Any, Dict, List

@dispatch
def mul_by_two(x: Any):
    """Multiply numbers by two"""
    return x * 2

# Support for builtin typing module:

@mul_by_two.register()
def _(x: Dict[Any, int]):
    return {k: v * 2 for k, v in x.items()}

@mul_by_two.register()
def _(x: List[int]):
    return [i * 2 for i in x]

# lazy-loaded type hints:

@mul_by_two.register()
def _(x: 'pandas.DataFrame'):
    return x.select_dtypes(include='number') * 2

# Assert it all works as intended:

assert mul_by_two(3) == 6
assert mul_by_two([2, 3, 4]) == [4, 6, 8]
assert mul_by_two({'a': 2, 'b': 3}) == {'a': 4, 'b': 6}

# Testing lazy-load functionality:

try:
    import pandas as pd
except ModuleNotFoundError:
    pass
else:
    print(mul_by_two(pd.DataFrame({
        'a': range(10),
        'b': ['exclude me'] * 10
    })))
```

### Basic Example 2

```python
from dispatchlib import Dispatcher
from types import FunctionType

# You can call Dispatcher() to skip a implementation
# It's also useful for type-checking.

always_return_figure = Dispatcher()

assert isinstance(always_return_figure, Dispatcher)
assert isinstance(always_return_figure, FunctionType)

import matplotlib
import matplotlib.pyplot as plt


# Implementations can be chained together:

@always_return_figure.register('matplotlib.pyplot.Axes')
@always_return_figure.register('matplotlib.pyplot.Subplot')
def return_figure1(x):
    return x.figure

@always_return_figure.register('matplotlib.pyplot.Figure')
def return_figure2(x):
    return x


fig, ax = plt.subplots()

assert always_return_figure(ax) == always_return_figure(fig)

plt.close(fig)
```

### Metadispatch example

```python
from dispatchlib import dispatch
from dispatchlib import metadispatch

class HTTPException(Exception):
    status_code: int

class PageNotFoundError(HTTPException):
    status_code: int = 404

class ForbiddenError(HTTPException):
    status_code: int = 403

custom_metadispatcher = metadispatch()

# This metadispatcher knows how to interpret when a user registers a function
# with an integer: The integer represents an HTTP status code.

@custom_metadispatcher.register(lambda val: isinstance(val, int))
def _(val: int):
    def checker(x: HTTPException):
        return x.status_code == val
    return checker

@dispatch(metadispatcher=custom_metadispatcher)
def status_code_message(code):
    raise TypeError('Unknown status code.')

@status_code_message.register(404)
def _(code):
    return 'Page not found.'

@status_code_message.register(403)
def _(code):
    return 'Forbidden.'

assert status_code_message(PageNotFoundError()) == 'Page not found.'
assert status_code_message(ForbiddenError()) == 'Forbidden.'
```

## Warning

I'm currently using Dispatchlib as part of another larger project. Dispatchlib exists separately of that project because I think it makes sense as its own separate thing. With that said, I plan on doing some bugfixing of use-cases as that project unfolds. So for this version of dispatchlib:

- There may be some bugs. 
- The API may break between changes.

When this message is no longer here, consider the module more stable.

### Todo

- create `dispatchmethod` akin to singledispatchmethod.
- decorator for making functions and methods dispatchable without immediately registering them to a dispatcher.
- support MRO for dispatching somehow.
- make code faster.
- make code more DRY via abstracting out the shared stuff in both `metadispatch` and `dispatch`.
- flesh out docs.
- add unit-tests.