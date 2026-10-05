"""FORCE_PLAN: every account is on a fixed plan with no Stripe subscription."""
import asyncio

from cloud import config, metering


def _patch_ledger(monkeypatch):
    async def no_sub(session, user_id):
        return None

    async def used(session, user_id, period_end):
        return metering._D(5)

    async def no_topups(session, user_id):
        return []

    monkeypatch.setattr(metering, "_subscription_row", no_sub)
    monkeypatch.setattr(metering, "_plan_used_this_period", used)
    monkeypatch.setattr(metering, "_topups_fifo", no_topups)


def test_default_is_pro():
    assert config.FORCE_PLAN == "pro"


def test_balance_reports_forced_plan(monkeypatch):
    _patch_ledger(monkeypatch)
    monkeypatch.setattr(config, "FORCE_PLAN", "pro")
    monkeypatch.setattr(config, "FORCE_PLAN_MINUTES", 1000)
    b = asyncio.run(metering._balance(None, "u1", user=object()))
    assert b["plan"] == "pro"
    assert b["plan_allowance"] == 1000
    assert b["remaining"] == 995
    assert b["period_end"] == metering.free_period_end()


def test_forced_plan_is_never_free(monkeypatch):
    monkeypatch.setattr(config, "FORCE_PLAN", "pro")
    assert asyncio.run(metering.is_free_user(None, "u1")) is False


def test_unset_restores_normal_plans(monkeypatch):
    _patch_ledger(monkeypatch)
    monkeypatch.setattr(config, "FORCE_PLAN", None)

    class NotEligible:
        free_plan_denied = True

    b = asyncio.run(metering._balance(None, "u1", user=NotEligible()))
    assert b["plan"] is None
    assert b["remaining"] == 0
