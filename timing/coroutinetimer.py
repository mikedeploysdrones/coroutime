import functools
import inspect
import sys
import time

from tornado import gen

import logger
log = logger.getLogger(__name__)

STAT_NAME = "my.coroutine.time"


def time_coroutine(f):
    name = []  # this is an array to allow access to a nonlocal variable from a wrapper

    @gen.coroutine
    @functools.wraps(f)
    def time_coroutine_wrapper(*args, **kwargs):
        if not name:
            classname = utils.get_method_classname(f, args)
            identifiers = (inspect.getmodule(f).__name__, classname or f.__name__)
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
                    future = g.send(yielded)
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

    def getRuntime(self):
        return self.runtime

    def finalize(self):
        stats_function(STAT_NAME, self.runtime, tags=["name:" + self.identifier])


def get_method_classname(method, args):
    """Retrieve a classname from a method given the method and the arguments being invoked.

    This function relies on methods using the conventional "self" as the name of its first argument.
    If the given method does not turn out to be a method (i.e. it's just a function), then None is
    returned. This function is useful in decorators where we cannot determine if the function that
    has been decorated is bound to an instance.

    Args:
        method - the function to check
        args - the arguments that were given to the method invocation

    Returns:
        the name of the class of the object to which method is bound, or None
    """
    argspec = inspect.getargspec(method)
    ismethod = len(argspec) >= 1 and argspec.args[0] == 'self'
    classname = args[0].__class__.__name__ if ismethod else None
    return classname


def stats_function(*args, **kwargs):
    """Overwrite this with you stats logging function."""
    pass
