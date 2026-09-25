"""Shared fixtures: an in-memory payments DB, a request factory, and a two-thread race."""

import threading

import pytest

from tests.fakes import FakeDB, FakeRequest


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def make_request():
    return lambda key, body: FakeRequest(merchant_id=1, key=key, body=body)


@pytest.fixture
def race():
    def run(fn, times):
        results = [None] * times
        barrier = threading.Barrier(times)

        def worker(index):
            barrier.wait()
            results[index] = fn()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(times)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    return run
