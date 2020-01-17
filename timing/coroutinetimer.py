import functools
import inspect
import logging
import sys
import time

from tornado import gen


log = logging.getLogger(__name__)


def time_coroutine(f):
    if not inspect.isgeneratorfunction(f):
        # function could be decorated as a coroutine, but isn't really a coroutine
        log.warning("Function %s is not a generator function and cannot be timed", f.__qualname__)
        return f

    name = []  # this is an array to allow access to a nonlocal variable from a wrapper

    @functools.wraps(f)
    def time_coroutine_wrapper(*args, **kwargs):
        if not name:
            identifier = ".".join((inspect.getmodule(f).__name__, f.__qualname__))
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
                    try:
                        future = g.throw(*exc_args)
                    except StopIteration as si:
                        raise gen.Return(si.value)
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
        stats_function(self)


def coroutime(f):
    """A convenience decorator that can be used in place of
    @gen.coroutine
    @time_coroutine
    """
    return gen.coroutine(time_coroutine(f))


def stats_function(timer):
    """Overwrite this with your stats logging function."""
    log.debug(f"{timer.identifier} ran for {timer.runtime:.2f}")
