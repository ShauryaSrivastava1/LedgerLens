"""
CSV exports for portfolio holdings and the watchlist. Plain stdlib csv
module — no pandas dependency needed for output this simple, and keeping
column order/formatting explicit here (rather than dumping a dataframe)
makes it easy to see exactly what a user gets when they open the file.
"""

import csv
import io

from app.services.portfolio import PortfolioSummary


def generate_portfolio_csv(summary: PortfolioSummary) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "symbol", "name", "sector", "quantity", "average_buy_price", "invested_amount",
            "current_price", "price_as_of", "current_value", "unrealized_pnl",
            "unrealized_pnl_pct", "target_allocation_pct", "actual_allocation_pct",
        ]
    )
    for h in summary.holdings:
        writer.writerow(
            [
                h.symbol, h.name, h.sector or "", h.quantity, h.average_buy_price, h.invested_amount,
                h.current_price if h.current_price is not None else "",
                h.price_as_of if h.price_as_of is not None else "",
                h.current_value if h.current_value is not None else "",
                h.unrealized_pnl if h.unrealized_pnl is not None else "",
                f"{h.unrealized_pnl_pct:.2f}" if h.unrealized_pnl_pct is not None else "",
                h.target_allocation_pct if h.target_allocation_pct is not None else "",
                f"{h.actual_allocation_pct:.2f}" if h.actual_allocation_pct is not None else "",
            ]
        )
    return buffer.getvalue()


def generate_watchlist_csv(items: list, companies: dict) -> str:
    """
    items: list[models.WatchlistItem]
    companies: {company_id: models.Company} lookup for the items above
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["symbol", "name", "sector", "note", "added_at"])
    for item in items:
        company = companies.get(item.company_id)
        writer.writerow(
            [
                company.symbol if company else "",
                company.name if company else "",
                (company.sector or "") if company else "",
                item.note or "",
                item.added_at.isoformat(),
            ]
        )
    return buffer.getvalue()
