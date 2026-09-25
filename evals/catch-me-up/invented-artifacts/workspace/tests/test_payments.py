"""Duplicate-submit and concurrent-retry cases for POST /payments."""

from api.payments import create_payment


def test_duplicate_submit_replays_first_response(fake_db, make_request):
    first = create_payment(make_request(key="k1", body={"amount": 500}), fake_db)
    second = create_payment(make_request(key="k1", body={"amount": 500}), fake_db)

    assert second == first
    assert fake_db.charge_count == 1


def test_concurrent_retry_charges_once(fake_db, make_request, race):
    responses = race(
        lambda: create_payment(make_request(key="k2", body={"amount": 500}), fake_db),
        times=2,
    )

    assert responses[0] == responses[1]
    assert fake_db.charge_count == 1


def test_reused_key_with_new_body_is_rejected(fake_db, make_request):
    create_payment(make_request(key="k3", body={"amount": 500}), fake_db)
    response = create_payment(make_request(key="k3", body={"amount": 900}), fake_db)

    assert response.status == 409
