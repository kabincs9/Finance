import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Custom filter for USD formatting in templates
app.jinja_env.filters["usd"] = usd


@app.after_request
def after_request(response):
    """Disable caching to ensure fresh data is always shown."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    # to get user's cash balance
    user = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = user[0]["cash"]

    # Get all stock holdings grouped by symbol
    rows = db.execute("""
        SELECT symbol, SUM(shares) as total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    portfolio = []
    total_value = cash

    for row in rows:
        quote = lookup(row["symbol"])
        if quote is None:
            return apology("Could not fetch stock price")
        total = quote["price"] * row["total_shares"]
        portfolio.append({
            "symbol": row["symbol"],
            "name": quote["name"],
            "shares": row["total_shares"],
            "price": quote["price"],
            "total": total
        })
        total_value += total

    return render_template("index.html", portfolio=portfolio, cash=cash, total=total_value)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("must provide username and password")

        if password != confirmation:
            return apology("passwords do not match")

        hash_pw = generate_password_hash(password)

        try:
            new_user_id = db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username, hash_pw
            )
        except:
            return apology("username already exists")

        session["user_id"] = new_user_id
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("must provide username and password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password")

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/login")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("missing symbol")

        quote = lookup(symbol)
        if quote is None:
            return apology("invalid symbol")

        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("missing symbol")
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("invalid number of shares")

        shares = int(shares)

        quote = lookup(symbol)
        if quote is None:
            return apology("invalid symbol")

        user_id = session["user_id"]
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        total_price = shares * quote["price"]

        if total_price > user_cash:
            return apology("can't afford")

        # update user cash
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_price, user_id)

        # to record transaction
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            user_id, symbol.upper(), shares, quote["price"]
        )

        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    user_id = session["user_id"]

    # to get list of stocks owned by user
    stocks = db.execute("""
        SELECT symbol, SUM(shares) as total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("missing symbol")
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("invalid number of shares")

        shares = int(shares)

        # to check if user owns enough shares
        owned_shares = 0
        for stock in stocks:
            if stock["symbol"] == symbol:
                owned_shares = stock["total_shares"]
                break
        if shares > owned_shares:
            return apology("too many shares")

        quote = lookup(symbol)
        if quote is None:
            return apology("invalid symbol")

        total_price = shares * quote["price"]

        # to  update user cash (adding back sale money)
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_price, user_id)

        # to record transaction as negative shares (selling..)
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            user_id, symbol.upper(), -shares, quote["price"]
        )

        flash("Sold!")
        return redirect("/")

    else:
        return render_template("sell.html", stocks=stocks)


@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    user_id = session["user_id"]

    transactions = db.execute("""
        SELECT symbol, shares, price, transacted
        FROM transactions
        WHERE user_id = ?
        ORDER BY transacted DESC
    """, user_id)

    return render_template("history.html", transactions=transactions)
# main thing is we need to create all new file in html
