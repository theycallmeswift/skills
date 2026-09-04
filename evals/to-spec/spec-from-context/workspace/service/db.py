"""Thin DB helpers used by the read/write paths."""

from __future__ import annotations


def query_one(sql: str, *params: object) -> dict:
    raise NotImplementedError


def execute(sql: str, *params: object) -> None:
    raise NotImplementedError
