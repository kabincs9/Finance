from flask import Blueprint, session, jsonify
from cs50 import SQL
from helpers import login_required, lookup

# Create Blueprint (separate module)
analytics = Blueprint("analytics", __name__)

# Database connection
db = SQL("sqlite:///finance.db")


@analytics.route("/analytics-data")
@login_required
def analytics_data():
    """
    Returns portfolio analytics as JSON.
    This does NOT interfere with existing routes.
    """

    user_id = session["user_id"]

    # Get user's stock holdings
    rows = db.execute("""
        SELECT symbol, SUM(shares) as total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    total_value = 0
    total_shares = 0
    portfolio = []

    for row in rows:
        quote = lookup(row["symbol"])

        if quote:
            value = quote["price"] * row["total_shares"]

            portfolio.append({
                "symbol": row["symbol"],
                "shares": row["total_shares"],
                "price": quote["price"],
                "value": value
            })

            total_value += value
            total_shares += row["total_shares"]

    # Return data as JSON (can be used later for charts/UI)
    return jsonify({
        "total_value": total_value,
        "total_shares": total_shares,
        "stock_count": len(portfolio),
        "portfolio": portfolio
    })
