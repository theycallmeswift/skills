# Widget Service

A small service backing the widget API.

- Reads go through `service/reads.py` (`read_widget`).
- Writes go through `service/writes.py` (`write_widget`).

Both talk to the database directly today. There is no caching layer.
