"""Admin analytics router: Cruscotto (executive KPIs) + PDF export.

Factory pattern: `build_router(db, require_admin)` returns an `APIRouter` that
can be mounted under the main `/api` prefix. Avoids circular imports with the
monolithic `server.py`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as _FastResponse


def _first_of_next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1)
    return dt.replace(month=dt.month + 1)


def _first_of_prev_month(dt: datetime) -> datetime:
    if dt.month == 1:
        return dt.replace(year=dt.year - 1, month=12)
    return dt.replace(month=dt.month - 1)


async def _sum_revenue(db, gte: datetime, lt: datetime) -> Dict[str, int]:
    pipeline = [
        {"$match": {"payment_status": "paid", "paid_at": {"$gte": gte, "$lt": lt}}},
        {"$group": {
            "_id": None,
            "gross": {"$sum": "$amount"},
            "platform_fee": {"$sum": "$platform_fee_amount"},
            "therapist": {"$sum": "$therapist_amount"},
            "count": {"$sum": 1},
        }},
    ]
    async for row in db.payment_transactions.aggregate(pipeline):
        return {
            "gross_cents": row.get("gross", 0) or 0,
            "platform_fee_cents": row.get("platform_fee", 0) or 0,
            "therapist_cents": row.get("therapist", 0) or 0,
            "count": row.get("count", 0) or 0,
        }
    return {"gross_cents": 0, "platform_fee_cents": 0, "therapist_cents": 0, "count": 0}


async def _batch_lookup_therapists(db, terapeuta_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch multiple therapists in a single $in query (kills N+1)."""
    if not terapeuta_ids:
        return {}
    obj_ids = []
    for tid in terapeuta_ids:
        try:
            obj_ids.append(ObjectId(tid))
        except Exception:
            continue
    out: Dict[str, Dict[str, Any]] = {}
    async for t in db.terapisti.find({"_id": {"$in": obj_ids}}):
        out[str(t["_id"])] = t
    return out


async def _compute_cruscotto(db) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month_start = _first_of_next_month(month_start)
    prev_month_start = _first_of_prev_month(month_start)

    # Revenue current + previous month
    rev_current = await _sum_revenue(db, month_start, next_month_start)
    rev_previous = await _sum_revenue(db, prev_month_start, month_start)

    # Pending payouts
    pending_agg = [
        {"$match": {"payment_status": "paid", "payout_status": {"$ne": "paid"}}},
        {"$group": {"_id": None, "total": {"$sum": "$therapist_amount"}, "count": {"$sum": 1}}},
    ]
    pending_payouts = {"total_cents": 0, "count": 0}
    async for row in db.payment_transactions.aggregate(pending_agg):
        pending_payouts = {"total_cents": row.get("total", 0) or 0, "count": row.get("count", 0) or 0}

    # Sessions this month
    month_start_iso = month_start.isoformat()
    next_month_iso = next_month_start.isoformat()
    sessions_completed_month = await db.appuntamenti.count_documents({
        "stato": "completato",
        "data_ora": {"$gte": month_start_iso, "$lt": next_month_iso},
    })
    sessions_booked_month = await db.appuntamenti.count_documents({
        "stato": {"$in": ["confermato", "completato"]},
        "data_ora": {"$gte": month_start_iso, "$lt": next_month_iso},
    })
    completion_rate = (
        round((sessions_completed_month / sessions_booked_month) * 100, 1)
        if sessions_booked_month > 0 else 0
    )

    # Revenue 6 months
    six_months_ago = month_start
    for _ in range(5):
        six_months_ago = _first_of_prev_month(six_months_ago)
    monthly_pipeline = [
        {"$match": {"payment_status": "paid", "paid_at": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": {"y": {"$year": "$paid_at"}, "m": {"$month": "$paid_at"}},
            "gross": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    buckets: Dict[str, Dict[str, int]] = {}
    async for row in db.payment_transactions.aggregate(monthly_pipeline):
        key = f"{row['_id']['y']}-{row['_id']['m']:02d}"
        buckets[key] = {"gross_cents": row.get("gross", 0) or 0, "count": row.get("count", 0) or 0}
    revenue_6m = []
    cursor = six_months_ago
    for _ in range(6):
        key = f"{cursor.year}-{cursor.month:02d}"
        b = buckets.get(key, {"gross_cents": 0, "count": 0})
        revenue_6m.append({
            "month": key,
            "label": cursor.strftime("%b").capitalize(),
            "gross_cents": b["gross_cents"],
            "count": b["count"],
        })
        cursor = _first_of_next_month(cursor)

    # Top 5 therapists (batch lookup — no N+1)
    top_pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": "$terapeuta_id", "gross": {"$sum": "$amount"}, "sessions": {"$sum": 1}}},
        {"$sort": {"gross": -1}},
        {"$limit": 5},
    ]
    top_rows: List[Dict[str, Any]] = []
    async for row in db.payment_transactions.aggregate(top_pipeline):
        top_rows.append(row)
    top_map = await _batch_lookup_therapists(db, [r["_id"] for r in top_rows])
    top_therapists = []
    for row in top_rows:
        tid = row["_id"]
        t = top_map.get(tid)
        top_therapists.append({
            "terapeuta_id": tid,
            "nome": f"{t.get('nome','')} {t.get('cognome','')}".strip() if t else "Sconosciuto",
            "gross_cents": row.get("gross", 0) or 0,
            "sessions": row.get("sessions", 0) or 0,
        })

    # IBAN missing (batch lookup — no N+1)
    iban_pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {
            "_id": "$terapeuta_id",
            "sessions": {"$sum": 1},
            "pending": {"$sum": {"$cond": [{"$ne": ["$payout_status", "paid"]}, "$therapist_amount", 0]}},
        }},
    ]
    iban_rows: List[Dict[str, Any]] = []
    async for row in db.payment_transactions.aggregate(iban_pipeline):
        iban_rows.append(row)
    iban_map = await _batch_lookup_therapists(db, [r["_id"] for r in iban_rows])
    iban_missing = []
    for row in iban_rows:
        tid = row["_id"]
        t = iban_map.get(tid)
        if not t:
            continue
        iban = (t.get("iban") or "").strip()
        pending_cents = row.get("pending", 0) or 0
        if not iban and pending_cents > 0:
            iban_missing.append({
                "terapeuta_id": tid,
                "nome": f"{t.get('nome','')} {t.get('cognome','')}".strip(),
                "sessions": row.get("sessions", 0) or 0,
                "pending_cents": pending_cents,
            })

    delta_percent = None
    if rev_previous["gross_cents"] > 0:
        delta_percent = round(
            ((rev_current["gross_cents"] - rev_previous["gross_cents"]) / rev_previous["gross_cents"]) * 100, 1
        )

    return {
        "generated_at": now.isoformat(),
        "revenue": {
            "current_month": rev_current,
            "previous_month": rev_previous,
            "delta_percent": delta_percent,
        },
        "pending_payouts": pending_payouts,
        "sessions_month": {
            "completed": sessions_completed_month,
            "booked": sessions_booked_month,
            "completion_rate": completion_rate,
        },
        "revenue_6m": revenue_6m,
        "top_therapists": top_therapists,
        "iban_missing": iban_missing,
    }


def build_router(db, require_admin) -> APIRouter:
    """Create an APIRouter with all Cruscotto endpoints bound to the given deps."""
    router = APIRouter()

    @router.get("/admin/cruscotto")
    async def admin_cruscotto(user: dict = Depends(require_admin)):
        """Executive KPIs for BIDOC admin: revenue, payouts, sessions, top therapists, IBAN alerts."""
        return await _compute_cruscotto(db)

    @router.get("/admin/cruscotto/report.pdf")
    async def admin_cruscotto_pdf(user: dict = Depends(require_admin)):
        """Export the Cruscotto KPIs as a monthly executive PDF report."""
        try:
            from cruscotto_pdf import build_cruscotto_pdf
        except ImportError:
            raise HTTPException(500, "PDF renderer non disponibile")
        data = await _compute_cruscotto(db)
        pdf_bytes = build_cruscotto_pdf(data)
        now = datetime.now(timezone.utc)
        filename = f"cruscotto-{now.year}-{now.month:02d}.pdf"
        return _FastResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router
