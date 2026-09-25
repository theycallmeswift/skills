"""In-memory stand-ins for the payments DB and request objects."""

import contextlib
import threading
from dataclasses import dataclass, field


@dataclass
class FakeRequest:
    merchant_id: int
    key: str
    body: dict
    headers: dict = field(init=False)

    def __post_init__(self):
        self.headers = {"Idempotency-Key": self.key}


class FakeDB:
    class UniqueViolation(Exception):
        pass

    def __init__(self):
        self.rows = {}
        self.charge_count = 0
        self._lock = threading.Lock()

    @contextlib.contextmanager
    def transaction(self):
        yield

    savepoint = transaction

    def rollback_to_savepoint(self):
        pass

    def find_idempotency(self, merchant_id, key):
        return self.rows.get((merchant_id, key))

    def insert_idempotency(self, merchant_id, key, body_hash):
        with self._lock:
            if (merchant_id, key) in self.rows:
                raise self.UniqueViolation
            self.rows[(merchant_id, key)] = _Row(body_hash)

    def charge(self, request):
        self.charge_count += 1
        return {"status": 201, "amount": request.body["amount"]}

    def store_response(self, merchant_id, key, response):
        self.rows[(merchant_id, key)].response = response


@dataclass
class _Row:
    body_hash: str
    response: object = None
