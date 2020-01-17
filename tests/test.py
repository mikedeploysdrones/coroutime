import inspect
import logging
import time
import unittest.mock
from asyncio import Handle, format_helpers

from tornado import gen
from tornado.gen import Return
from tornado.testing import AsyncTestCase, gen_test

import timing
from timing.coroutinetimer import time_coroutine


def is_all(func):
    print(func.__name__)
    for is_f_name in vars(inspect):
        if is_f_name.startswith("is") and inspect.isfunction(is_f := getattr(inspect, is_f_name)):
            is_it = is_f(func)
            print(f"{is_f_name}\t{is_it}")


@gen.coroutine
def layered_sleeper(t):
    result = yield sleeper(t)
    raise Return(result)


@gen.coroutine
@time_coroutine
def multisleeper(t):
    time.sleep(t)
    yield gen.sleep(5)
    time.sleep(t)
    yield gen.sleep(0)
    time.sleep(t)
    yield asyncio.sleep(1)
    time.sleep(2*t)
    return 2*t


@gen.coroutine
def sleep_sleep(*times):
    iter_times = iter(times)
    try:
        while True:
            t0 = next(iter_times)
            time.sleep(t0)
            t1 = next(iter_times)
            yield gen.sleep(t1)
    except StopIteration:
        pass


@gen.coroutine
@time_coroutine
def sleeper(t):
    time.sleep(t)
    yield asyncio.sleep(0)
    return 2*t


@gen.coroutine
@time_coroutine
def no_yield_path_sleep(t):
    time.sleep(t)
    if False:
        yield asyncio.sleep(0)
    return 2*t


@gen.coroutine
def not_a_generator_raise_return(t):
    raise Return(2*t)


@gen.coroutine
def not_a_generator_return(t):
    return 2*t


def make_sleeper(x, asynchronous=False):
    @gen.coroutine
    @timing.coroutinetimer.time_coroutine
    def sleeper(self):
        yield gen.sleep(0)
        time.sleep(x)

    @gen.coroutine
    def asleeper(self):
        yield gen.sleep(x)

    return asleeper if asynchronous else sleeper


class MemberSleep(object):
    @classmethod
    @gen.coroutine
    @time_coroutine
    def sleep_inside_cls(cls, t):
        time.sleep(t)
        yield gen.sleep(0)
        return 2*t


class TestTimeCoroutine(AsyncTestCase):

    @gen_test
    def test_time_coroutine_0(self):
        duration = 0.5
        with unittest.mock.patch('timing.coroutinetimer.stats_function') as mock_sf:
            result = yield no_yield_path_sleep(duration)
            self.assertEqual(result, 2 * duration)
        mock_sf.assert_called_once()
        timer = mock_sf.call_args.args[0]
        self.assertAlmostEqual(duration, timer.runtime, delta=0.01)
        self.assertEqual(timer.identifier, 'tests.test.no_yield_path_sleep')

    @gen_test
    def test_time_coroutine_1(self):
        duration = 0.5
        with unittest.mock.patch('timing.coroutinetimer.stats_function') as mock_sf:
            result = yield not_a_generator_return(duration)
            self.assertEqual(result, 2 * duration)
        assert not mock_sf.called
        assert time_coroutine(not_a_generator_return) is not_a_generator_return

    @gen_test
    def test_time_coroutine_2(self):
        duration = 0.5
        with unittest.mock.patch('timing.coroutinetimer.stats_function') as mock_sf:
            result = yield not_a_generator_raise_return(duration)
            self.assertEqual(result, 2 * duration)
        assert not mock_sf.called
        assert time_coroutine(not_a_generator_raise_return) is not_a_generator_raise_return

    @gen_test
    def test_time_coroutine_3(self):
        # check that
        duration = 0.5
        with unittest.mock.patch('timing.coroutinetimer.stats_function') as mock_sf:
            result = yield layered_sleeper(duration)
            self.assertEqual(result, 2 * duration)
        mock_sf.assert_called_once()
        timer = mock_sf.call_args.args[0]
        self.assertAlmostEqual(duration, timer.runtime, 2)

    @gen_test
    def test_member_sleep(self):
        duration = 0.5
        with unittest.mock.patch('timing.coroutinetimer.stats_function') as mock_sf:
            result = yield MemberSleep.sleep_inside_cls(duration)
            self.assertEqual(result, 2 * duration)
        mock_sf.assert_called_once()
        timer = mock_sf.call_args.args[0]
        self.assertAlmostEqual(duration, timer.runtime, delta=0.01)
        self.assertEqual(timer.identifier, 'tests.test.MemberSleep.sleep_inside_cls')

    @gen_test(timeout=20)
    def test_multisleeper(self):
        duration = 0.5
        with unittest.mock.patch('timing.coroutinetimer.stats_function') as mock_sf:
            result = yield multisleeper(duration)
            self.assertEqual(result, 2 * duration)
        mock_sf.assert_called_once()
        timer = mock_sf.call_args.args[0]
        self.assertAlmostEqual(5 * duration, timer.runtime, delta=0.02)
        self.assertEqual(timer.identifier, 'tests.test.multisleeper')
