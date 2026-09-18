import pytest

from waypoint.delivery import DeliveryLedger


async def test_uncertain_write_delivery_cannot_be_retried():
    ledger = DeliveryLedger()
    deliveries = []

    async def lose_acknowledgement():
        deliveries.append("write reached synthetic receiver")
        raise TimeoutError("acknowledgement lost")

    with pytest.raises(TimeoutError):
        await ledger.attempt("write-1", lose_acknowledgement)
    assert ledger.effect("write-1") == "uncertain"
    with pytest.raises(ValueError, match="retry refused"):
        await ledger.attempt("write-1", lose_acknowledgement)
    assert len(deliveries) == 1
