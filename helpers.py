# Stock Trading Website

# A helper file to be used in conjunction with application.py.

import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps

# Render message as an apology to user.
def apology(message, code=400):
    def escape(s):
        # Escape special characters.
        # https://github.com/jacebrowning/memegen#special-characters
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


# Decorate routes to require login.
# http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Look up quote for symbol.
def lookup(symbol):
    # Contact API.
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None
    # Parse response.
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


# Format value as USD.
def usd(value):
    return f"${value:,.2f}"
