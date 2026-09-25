"""Regression tests for the in_corso → completato auto-transition.

Bug fixed: no_show_service.py sets stato=in_corso at start+15min when both
participants attended, but had no hook to advance to completato. Sessions
were stuck in_corso forever until admin marked them manually.

Fix (booking_service.py):
- _auto_complete_appointment(app_id): flips in_corso → completato if row still there
- sweep_stale_in_corso(): startup sweep that catches historical stuck rows
- Wire: called before _send_review_invite_email + on server startup
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

import pytest
from bson import ObjectId

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


@pytest.fixture(autouse=True)
def _bind_db_to_current_loop(monkeypatch):
    """booking_service.db was bound to the event loop that existed at import
    time; each asyncio test spawns a fresh loop, so we hot-swap the module-level
    client for one bound to the current loop. Keeps the tests self-contained."""
    import booking_service
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    monkeypatch.setattr(booking_service, "db", client[os.environ["DB_NAME"]])
    yield


def _db():
    """Fresh client bound to the current event loop, for test setup/teardown."""
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.mark.asyncio
async def test_auto_complete_ended_session_transitions_to_completato():
    from booking_service import _auto_complete_appointment
    db = _db()
    appt_id = ObjectId()
    await db.appuntamenti.insert_one({
        "_id": appt_id,
        "stato": "in_corso",
        "data_ora": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "durata_minuti": 50,
        "_test_regression": True,
    })
    try:
        await _auto_complete_appointment(str(appt_id))
        row = await db.appuntamenti.find_one({"_id": appt_id})
        assert row["stato"] == "completato"
        assert row["completato_source"] == "auto_post_session"
        assert row["completato_at"] is not None
    finally:
        await db.appuntamenti.delete_one({"_id": appt_id})


@pytest.mark.asyncio
async def test_auto_complete_does_not_overwrite_already_completed():
    """Idempotency: calling on an already-completato row is a no-op."""
    from booking_service import _auto_complete_appointment
    db = _db()
    appt_id = ObjectId()
    original_completato_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await db.appuntamenti.insert_one({
        "_id": appt_id,
        "stato": "completato",
        "completato_at": original_completato_at,
        "completato_source": "manual",
        "data_ora": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "durata_minuti": 50,
        "_test_regression": True,
    })
    try:
        await _auto_complete_appointment(str(appt_id))
        row = await db.appuntamenti.find_one({"_id": appt_id})
        assert row["completato_source"] == "manual"  # not overwritten
        # Mongo may strip tzinfo when reading back — compare naive vs naive
        stored = row["completato_at"]
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert stored == original_completato_at
    finally:
        await db.appuntamenti.delete_one({"_id": appt_id})


@pytest.mark.asyncio
async def test_sweep_only_touches_ended_in_corso_sessions():
    """The sweep must NOT prematurely complete a session that is still within
    its scheduled duration + 30min grace period."""
    from booking_service import sweep_stale_in_corso
    db = _db()
    now = datetime.now(timezone.utc)
    # Fresh in-progress session — should be LEFT ALONE
    fresh_id = ObjectId()
    await db.appuntamenti.insert_one({
        "_id": fresh_id,
        "stato": "in_corso",
        "data_ora": (now - timedelta(minutes=5)).isoformat(),
        "durata_minuti": 50,
        "_test_regression": True,
    })
    # Stale — should be swept
    stale_id = ObjectId()
    await db.appuntamenti.insert_one({
        "_id": stale_id,
        "stato": "in_corso",
        "data_ora": (now - timedelta(hours=3)).isoformat(),
        "durata_minuti": 50,
        "_test_regression": True,
    })
    try:
        n = await sweep_stale_in_corso()
        assert n >= 1  # at least our stale row (could be more if the env has others)
        fresh = await db.appuntamenti.find_one({"_id": fresh_id})
        stale = await db.appuntamenti.find_one({"_id": stale_id})
        assert fresh["stato"] == "in_corso", "fresh session must not be prematurely closed"
        assert stale["stato"] == "completato", "stale session must be auto-completed"
        assert stale["completato_source"] == "sweep_startup"
    finally:
        await db.appuntamenti.delete_many({"_id": {"$in": [fresh_id, stale_id]}})


@pytest.mark.asyncio
async def test_sweep_ignores_non_in_corso_states():
    """Sweep must never touch confermato, cancellato, no_show_* states."""
    from booking_service import sweep_stale_in_corso
    db = _db()
    now = datetime.now(timezone.utc)
    ids = {}
    for stato in ["confermato", "cancellato", "no_show_paziente", "no_show_terapeuta", "prenotato"]:
        aid = ObjectId()
        ids[stato] = aid
        await db.appuntamenti.insert_one({
            "_id": aid,
            "stato": stato,
            "data_ora": (now - timedelta(hours=5)).isoformat(),
            "durata_minuti": 50,
            "_test_regression": True,
        })
    try:
        await sweep_stale_in_corso()
        for stato, aid in ids.items():
            row = await db.appuntamenti.find_one({"_id": aid})
            assert row["stato"] == stato, f"sweep must not touch stato={stato}"
    finally:
        await db.appuntamenti.delete_many({"_id": {"$in": list(ids.values())}})

