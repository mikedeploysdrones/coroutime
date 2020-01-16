import functools
import inspect
import logging
import sys
import time

from tornado import gen


log = logging.getLogger(__name__)

STAT_NAME = "my.coroutine.time"

def is_all(func):
    print(func.__name__)
    for is_f_name in vars(inspect):
        if is_f_name.startswith("is") and inspect.isfunction(is_f := getattr(inspect, is_f_name)):
            is_it = is_f(func)
            print(f"{is_f_name}\t{is_it}")


def time_coroutine(f):
    if not inspect.isgeneratorfunction(f):
        # function could be decorated as a coroutine, but isn't really a coroutine
        log.warning("Function %s is not a generator function and cannot be timed", f.__qualname__)
        return f

    name = []  # this is an array to allow access to a nonlocal variable from a wrapper

    print("\n\ntime_coroutine")
    is_all(f)

    @functools.wraps(f)
    def time_coroutine_wrapper(*args, **kwargs):
        if not name:
            classname = get_method_classname(f, args)
            identifiers = filter(None, (inspect.getmodule(f).__name__, classname, f.__name__))
            identifier = ".".join(identifiers)
            name.append(identifier)

        timer = Timer(name[0])
        with timer:
            g = f(*args, **kwargs)

        excepted = False
        yielded = None
        future = None
        while True:
            if excepted:
                excepted = False
            else:
                log.debug("sending %r into %s", yielded, name[0])
                with timer:
                    try:
                        future = g.send(yielded)
                    except StopIteration as si:
                        raise gen.Return(si.value)
            log.debug("yielding %r in %s", future, name[0])
            try:
                yielded = yield future
            except:
                exc_args = sys.exc_info()
                excepted = True
                log.debug("throwing %r in %s", exc_args[1], name[0])
                with timer:
                    future = g.throw(*exc_args)
                log.debug("throw returned %r in %s", future, name[0])
            else:
                log.debug("yielded %r from %s", yielded, name[0])
            finally:
                exc_args = None

    return time_coroutine_wrapper


class Timer(object):

    def __init__(self, identifier):
        self.identifier = identifier
        self.start_time = self.stop_time = None
        self.runtime = 0.0

    def __enter__(self):
        self.start_timer()
        return self

    def __exit__(self,  exc_type, exc_value, traceback):
        self.stop_timer()
        # if exc_type is not None, we exited due to an exception
        # which means this is the last time we will call this timer
        if exc_type is not None:
            self.finalize()

    def start_timer(self):
        assert self.start_time is None  # prevent restarting an unstopped timer
        self.start_time = time.time()

    def stop_timer(self):
        self.stop_time = time.time()
        self.runtime += self.stop_time - self.start_time
        self.start_time = None  # forces an error if we stop a Timer that has not been re/started

    def finalize(self):
        stats_function(STAT_NAME, self.runtime, tags=["name:" + self.identifier])


def get_method_classname(method, args):
    """Retrieve a classname from a method given the method and the arguments being invoked.

    This function relies on methods using the conventional "self" or "cls" as the name of its first argument.
    If the given method does not turn out to be a method (i.e. it's just a function), then None is
    returned. This function is useful in decorators where we cannot determine if the function that
    has been decorated is bound to an instance.

    Args:
        method - the function to check
        args - the arguments that were given to the method invocation

    Returns:
        the name of the class of the object to which method is bound, or None
    """
    class_ = None
    argspec = inspect.getfullargspec(method)
    ismethod = argspec.args and argspec.args[0] in ('self', 'cls')
    if ismethod:
        first = args[0]
        class_ = first if inspect.isclass(first) else first.__class__
    classname = class_ and class_.__name__
    return classname


def stats_function(*args, **kwargs):
    """Overwrite this with your stats logging function."""
    print(f"{args!r} {kwargs!r}")
