import pytest

from crisisroute.agents.messages import Message, MessageBus


def test_unknown_message_type_rejected():
    with pytest.raises(ValueError):
        Message(type="NOT_A_TYPE", sender="A", tick=0, payload={})


def test_direct_message_delivered_only_to_recipient():
    bus = MessageBus()
    bus.register("A")
    bus.register("B")
    bus.register("C")

    bus.send(Message(type="ASSIGNMENT", sender="A", tick=0, payload={}, recipient="B"))

    assert [m.type for m in bus.drain("B")] == ["ASSIGNMENT"]
    assert bus.drain("C") == []
    assert bus.drain("A") == []


def test_broadcast_message_delivered_to_everyone_except_sender():
    bus = MessageBus()
    bus.register("A")
    bus.register("B")
    bus.register("C")

    bus.send(Message(type="STATUS_UPDATE", sender="A", tick=0, payload={}))

    assert [m.type for m in bus.drain("B")] == ["STATUS_UPDATE"]
    assert [m.type for m in bus.drain("C")] == ["STATUS_UPDATE"]
    assert bus.drain("A") == []


def test_drain_clears_the_inbox():
    bus = MessageBus()
    bus.register("A")
    bus.register("B")
    bus.send(Message(type="TASK_COMPLETE", sender="A", tick=0, payload={}, recipient="B"))

    first = bus.drain("B")
    second = bus.drain("B")

    assert len(first) == 1
    assert second == []


def test_log_records_every_message_regardless_of_delivery():
    bus = MessageBus()
    bus.register("A")
    bus.register("B")

    bus.send(Message(type="ZONE_REPORT", sender="A", tick=0, payload={}, recipient="B"))
    bus.send(Message(type="REQUEST_HELP", sender="B", tick=1, payload={}))

    assert [m.type for m in bus.log] == ["ZONE_REPORT", "REQUEST_HELP"]


def test_log_for_tick_filters_by_tick():
    bus = MessageBus()
    bus.register("A")
    bus.send(Message(type="STATUS_UPDATE", sender="A", tick=0, payload={}))
    bus.send(Message(type="STATUS_UPDATE", sender="A", tick=1, payload={}))

    assert len(bus.log_for_tick(0)) == 1
    assert len(bus.log_for_tick(1)) == 1


def test_send_to_unregistered_recipient_raises():
    bus = MessageBus()
    bus.register("A")
    with pytest.raises(ValueError):
        bus.send(Message(type="ASSIGNMENT", sender="A", tick=0, payload={}, recipient="GHOST"))
