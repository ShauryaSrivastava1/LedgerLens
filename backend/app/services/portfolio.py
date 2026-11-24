"""
Builds a portfolio summary from a user's holdings.

Allocation is computed from cost basis (quantity x average_buy_price) —
that part is unchanged from Milestone 5. Milestone 6 adds mark-to-market
fields (current_value, unrealized_pnl, etc.) wherever PriceHistory data
exists for a company; a holding with no ingested price data gets nulls
for those fields, never a value silently derived from cost basis. Totals
(total_current_value etc.) are computed only from holdings that DO have
price data, with `all_holdings_priced` telling the caller whether that
total is complete or partial.
"""

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app import crud, models

DOWN_SIGNIFICANTLY_THRESHOLD_PCT = -15.0


@dataclass
class HoldingRow:
    holding_id: str
    company_id: str
    symbol: str
    name: str
    sector: Optional[str]
    quantity: Decimal
    average_buy_price: Decimal
    invested_amount: Decimal
    target_allocation_pct: Optional[Decimal]
    actual_allocation_pct: Optional[Decimal]  # share of total invested amount, cost-basis

    current_price: Optional[Decimal] = None
    price_as_of: Optional[datetime.date] = None
    price_staleness_days: Optional[int] = None
    current_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[float] = None
    down_significantly_from_buy: bool = False


@dataclass
class SectorAllocation:
    sector: str
    invested_amount: Decimal
    actual_allocation_pct: Decimal


@dataclass
class PortfolioSummary:
    total_invested: Decimal
    total_current_value: Optional[Decimal] = None
    total_unrealized_pnl: Optional[Decimal] = None
    total_unrealized_pnl_pct: Optional[float] = None
    all_holdings_priced: bool = False
    holdings: list[HoldingRow] = field(default_factory=list)
    sector_allocation: list[SectorAllocation] = field(default_factory=list)


def build_portfolio_summary(db: Session, user_id) -> PortfolioSummary:
    holdings = (
        db.query(models.Holding)
        .filter(models.Holding.user_id == user_id)
        .join(models.Company)
        .all()
    )

    total_invested = sum((h.quantity * h.average_buy_price for h in holdings), Decimal("0"))
    latest_prices = crud.get_latest_prices_for_companies(db, [h.company_id for h in holdings])
    today = datetime.date.today()

    rows: list[HoldingRow] = []
    sector_totals: dict[str, Decimal] = {}
    total_current_value = Decimal("0")
    priced_holdings_count = 0

    for h in holdings:
        invested = h.quantity * h.average_buy_price
        actual_pct = (invested / total_invested * 100) if total_invested > 0 else None

        row = HoldingRow(
            holding_id=str(h.id),
            company_id=str(h.company_id),
            symbol=h.company.symbol,
            name=h.company.name,
            sector=h.company.sector,
            quantity=h.quantity,
            average_buy_price=h.average_buy_price,
            invested_amount=invested,
            target_allocation_pct=h.target_allocation_pct,
            actual_allocation_pct=actual_pct,
        )

        price_record = latest_prices.get(h.company_id)
        if price_record is not None:
            current_value = h.quantity * price_record.close_price
            unrealized_pnl = current_value - invested
            unrealized_pnl_pct = float(unrealized_pnl / invested * 100) if invested > 0 else None

            row.current_price = price_record.close_price
            row.price_as_of = price_record.price_date
            row.price_staleness_days = (today - price_record.price_date).days
            row.current_value = current_value
            row.unrealized_pnl = unrealized_pnl
            row.unrealized_pnl_pct = unrealized_pnl_pct
            row.down_significantly_from_buy = (
                unrealized_pnl_pct is not None and unrealized_pnl_pct <= DOWN_SIGNIFICANTLY_THRESHOLD_PCT
            )

            total_current_value += current_value
            priced_holdings_count += 1

        rows.append(row)

        sector_key = h.company.sector or "Unclassified"
        sector_totals[sector_key] = sector_totals.get(sector_key, Decimal("0")) + invested

    sector_allocation = [
        SectorAllocation(
            sector=sector,
            invested_amount=amount,
            actual_allocation_pct=(amount / total_invested * 100) if total_invested > 0 else Decimal("0"),
        )
        for sector, amount in sorted(sector_totals.items(), key=lambda kv: kv[1], reverse=True)
    ]

    all_priced = len(holdings) > 0 and priced_holdings_count == len(holdings)

    total_unrealized_pnl = None
    total_unrealized_pnl_pct = None
    invested_in_priced_holdings = sum(
        (h.average_buy_price * h.quantity for h in holdings if h.company_id in latest_prices),
        Decimal("0"),
    )
    if priced_holdings_count > 0:
        total_unrealized_pnl = total_current_value - invested_in_priced_holdings
        if invested_in_priced_holdings > 0:
            total_unrealized_pnl_pct = float(total_unrealized_pnl / invested_in_priced_holdings * 100)

    return PortfolioSummary(
        total_invested=total_invested,
        total_current_value=total_current_value if priced_holdings_count > 0 else None,
        total_unrealized_pnl=total_unrealized_pnl,
        total_unrealized_pnl_pct=total_unrealized_pnl_pct,
        all_holdings_priced=all_priced,
        holdings=rows,
        sector_allocation=sector_allocation,
    )
