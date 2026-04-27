from functools import wraps
from flask import redirect, session
import requests
import os


def apology(message, code=400):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return (f"Sorry: {escape(message)}", code)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    try:
        api_key = os.environ.get("API_KEY")
        if not api_key:
            raise RuntimeError("API_KEY not set")
        url = f"https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"].upper()
        }
    except:
        return None


def usd(value):
    return f"${value:,.2f}"
