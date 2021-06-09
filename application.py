# Stock Trading Website

# A virtual stock trading Flask website. It includes features like registering a user account, 
# grabbing quotes for shares of stocks, virtual buying and selling of said stocks, 
# and being able to view a history of transactions.

# Built with Flask, Python, SQL, HTML, CSS, Jinja, and JavaScript.

# Use IEX API key to run the website locally from the terminal:
# In terminal:
# export API_KEY=pk_4c6df35359924235aa350943a92e1eb8
# --> flask run

import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Alex's imports:
from datetime import datetime

# Configure application.
app = Flask(__name__)

# Ensure templates are auto-reloaded.
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached.
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter.
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies).
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database.
db = SQL("sqlite:///finance.db")

# Make sure API key is set.
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Shows the user all of their owned stocks and cash information.
@app.route("/finance_index")
@login_required
def index():
    # Identify the current user.
    user_id = session["user_id"]
    # Get all rows in the stocks table for that user.
    user_stocks = db.execute("SELECT * FROM stocks WHERE user_id=:user_id", user_id=user_id)
    # Create a list to separate our stock's information.
    stock_info_list = []
    # Initialize variables here for correct scope.
    name = ""
    price = 0
    symbol = ""
    shares_total = 0
    shares_sum = 0
    # Create an array of stocks we've already looked at to prevent overcounting or overcalculating of shares and price.
    stocks_seen = []
    # A list of stock_attributes to be passed to finance_index.html.
    all_stocks = []
    # A sum of all the share totals at their current stock price.
    shares_total_sum = 0
    # Look up current price of each stock in the rows you've gotten, one by one, in user_stocks.
    for row in user_stocks:
        # Reset shares_sum for each stock
        shares_sum = 0
        # Get stock's name.
        stock_symbol = row["symbol"]
        # If we've already seen the stock, then continue to next loop and row.
        if stock_symbol in stocks_seen:
            continue
        # Otherwise, calculate information for this stock.
        else:
            # Get the symbol's information.
            stock_info = lookup(stock_symbol)
            # Clear stock_info_list so it appends correctly.
            stock_info_list.clear()
            # Parse the stock information into a list.
            for value in stock_info.values():
                stock_info_list.append(value)
            # Give each index their appropriate stock information declarations.
            name = stock_info_list[0]
            # Format the price using helpers.usd() to show its currency.
            price = usd(stock_info_list[1])
            # Get the unformatted_price too so we can use it to calculate our shares' total.
            unformatted_price = stock_info_list[1]
            # Get the symbol.
            symbol = stock_info_list[2]
            # Get number of shares for the stock in this loop (those that belong to CURRENT user) from stocks table,
            # then add them to get the total number of shares for this stock.
            all_shares = db.execute("SELECT shares FROM stocks WHERE symbol=:stock_symbol AND user_id=:user_id",
                                    stock_symbol=stock_symbol, user_id=user_id)
            # Transform dict values (as this is the format received from db.execute) in "shares" column to int from 
            # all_shares.
            for key in all_shares:
                # Calculate how many shares we have for this stock.
                shares_sum += int(key.get('shares'))
            # If we have more than zero shares of this stock (say, after selling all of it), we display it in HTML.
            # Otherwise, we won't display it.
            if not shares_sum < 1:
                # Multiply our shares_sum by the current price of the stock for our shares_total.
                shares_total = int(shares_sum) * float(unformatted_price)
                # Add this stock's shares_total to the shares_total_sum to be used in the grand_total calculation.
                shares_total_sum += shares_total
                # Consolidate attributes of this stock to an array.
                stock_attributes = []
                stock_attributes.append(symbol)
                stock_attributes.append(name)
                stock_attributes.append(shares_sum)
                stock_attributes.append(price)
                stock_attributes.append(usd(shares_total))
                # Add these attributes to an index in all_stocks.
                all_stocks.append(stock_attributes)
                # Add this stock to our stocks_seen array.
                stocks_seen.append(stock_symbol)

    # Clear our stock list for the next time this function is called.
    stocks_seen.clear()
    # Get how much cash the user currently has on hand.
    user_cash = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=user_id)
    formatted_cash = user_cash[0]
    unformatted_final_cash = float(formatted_cash['cash'])
    final_cash = usd(unformatted_final_cash)
    # Get the grand total, which will be our final cash plus the totals of all our stocks.
    grand_total = usd(unformatted_final_cash + shares_total_sum)
    # Render all of the user's stocks and their information, along with user's information, to the screen after they 
    # hit buy.
    return render_template("finance_index.html", all_stocks=all_stocks, final_cash=final_cash, grand_total=grand_total)


# Lets the user buy stock shares.
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    # User accesses the buy page to look up and buy stocks.
    if request.method == "GET":
        return render_template("buy.html")
    # User reached route via POST (as by submitting a form via POST), and entered some information.
    else:
        # Get symbol of stock from submitted form.
        symbol = request.form.get("symbol")
        # Get number of shares entered by the user.
        shares = request.form.get("shares")
        # Look up real time stock information via helpers.py lookup().
        stock_info = lookup(symbol)
        # If the user entered nothing or stock_info returns None, that means the stock does not exist
        # so we'll return an apology.
        if not symbol or stock_info == None:
            return apology("stock symbol not entered or stock symbol does not exist!", 403)
        # If the user entered nothing or a negative shares value, we issue an apology. Determining 
        # if a number is an int or float: https://note.nkmk.me/en/python-check-int-float/
        if not shares or int(shares) < 1 or isinstance(shares, float):
            return apology("share amount was not entered or entry was less than 1.", 403)
        # Get the stock's information to store in our stocks table.
        stock_info_list = []
        # If stock_info returns None, that means the stock does not exist so we'll return an apology.
        if stock_info == None:
            return apology("stock symbol does not exist!", 403)
        # Otherwise the stock does exist, and so we'll parse the stock information into our list.
        for value in stock_info.values():
            stock_info_list.append(value)
        # Give each index their appropriate declarations so we can use them correctly in our 
        # quoted.html template.
        name = stock_info_list[0]
        # Format the price using helpers.usd() to show its currency.
        price = usd(stock_info_list[1])
        # Create an unformatted_price to be used in our total variable calculation below.
        unformatted_price = stock_info_list[1]
        symbol = stock_info_list[2]
        # Get current user of session's id.
        user_id = session["user_id"]
        # Get time the transaction was made.
        transacted = datetime.now()
        # Get the amount of cash the user has from the row associated with their name in the users table.
        # session["user_id"] is our current user.
        # Get all rows with the user's id.
        cash = db.execute("SELECT cash FROM users WHERE id=:user_id",
                          user_id=user_id)
        # In this case, we will have one, unique ID for each user.
        cash_balance = cash[0]
        # Get total bought after calculating purchase.
        total = int(shares) * float(unformatted_price)
        # If user can afford number of shares at the current price, make the purchase.
        if total <= cash_balance['cash']:
            # Get user's new cash total. Use 'cash' to get the numerical value of the user's cash value for 
            # the row we are looking at.
            new_cash_total = cash_balance['cash'] - total
            # Change amount of user's cash in users after transaction.
            db.execute("UPDATE users SET cash=:new_cash_total WHERE id=:user_id",
                              user_id=user_id, new_cash_total=new_cash_total)
            # Insert stock's information into stocks table.
            db.execute("INSERT INTO stocks (user_id, symbol, name, shares, price, transacted) VALUES (:user_id, :symbol, :name, :shares, :price, :transacted)",
                              user_id=user_id, symbol=symbol, name=name, shares=shares, price=price, transacted=transacted)
            # Return HTML to the user.
            return index()
        # If user does not have enough money to make the purchase, return apology and don't make purchase.
        else:
            return apology("Sorry, not enough funds to make purchase", 403)


# Gets a user's past transactions.
@app.route("/history")
@login_required
def history():
    # Get the user id for current user.
    user_id = session["user_id"]
    # Fetch all necessary historical data from user's DB table.
    history = db.execute("SELECT symbol, shares, price, transacted FROM stocks WHERE user_id=:user_id", user_id=user_id)
    # A list of lists (rows) containing information from each of the user's transactions.
    history_list = []
    # Get only the values of each list entry, not the keys. Used with help from:
    # https://www.geeksforgeeks.org/python-get-values-of-particular-key-in-list-of-dictionaries/
    symbols = [sub['symbol'] for sub in history]
    shares = [sub['shares'] for sub in history]
    prices = [sub['price'] for sub in history]
    transacted = [sub['transacted'] for sub in history]
    # Append each value of the lists above to get list items that reflect the rows in our database.
    i = 0
    symbols_length = len(symbols)
    while i < symbols_length:
        # Each loop create a new list for a row (necessary to display values correctly to user),
        # then add that list to the history_list.
        row = []
        row.append(symbols[i])
        row.append(shares[i])
        row.append(prices[i])
        row.append(transacted[i])
        history_list.append(row)
        i += 1
    # Render the list to the user.
    return render_template("history.html", history_list=history_list)


# Lets a user log in.
@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id.
    session.clear()
    # User reached route via POST (as by submitting a form via POST).
    if request.method == "POST":
        # Ensure username was submitted.
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Ensure password was submitted.
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        # Query database for username.
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        # Ensure username exists and password is correct.
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)
        # Remember which user has logged in.
        session["user_id"] = rows[0]["id"]
        # Return the user to a page showing their stock portfolio and tool options.
        return index()
    # User reached route via GET (as by clicking a link or via redirect).
    else:
        return render_template("login.html")


# Let's a user log out.
@app.route("/logout")
def logout():
    # Forget any user_id.
    session.clear()
    # Redirect user to login form.
    return redirect("/")

# Gets a price quote for a stock in real time.
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    # Get quote page for user so user can lookup a stock.
    if request.method == "GET":
        return render_template("quote.html")
    # User queries for a stock's information.
    else:
        # Get symbol of stock from submitted form.
        symbol = request.form.get("symbol")
        # Create a list to separate our stock's information.
        stock_info_list = []
        # Look up real time stock information via helpers.py lookup().
        stock_info = lookup(symbol)
        # If stock_info returns None, that means the stock does not exist
        # so we'll return an apology.
        if stock_info == None:
            return apology("stock symbol does not exist!", 403)
        # Otherwise the stock does exist, and so we'll parse the stock information
        # into our list.
        for value in stock_info.values():
            stock_info_list.append(value)
        # Give each index their appropriate declarations so we can use them correctly
        # in our quoted.html template.
        name = stock_info_list[0]
        # Format the price using helpers.usd() to show its currency.
        price = usd(stock_info_list[1])
        symbol = stock_info_list[2]
        # Return our formatted stock's information.
        return render_template("quoted.html", name=name, price=price, symbol=symbol)

# Lets a new user register to the site.
@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST).
    # They entered information into the register.html form fields and submitted that information.
    if request.method == "POST":
        # Query database for username to see if any rows in the database contain it.
        username_row = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        # If the username field is left blank or the username already exists in the database, return apology.
        # "len(rows) == 1" means we already have a row that contains that username.
        if not request.form.get("username") or len(username_row) == 1:
            return apology("must provide username or username already exists", 403)
        # If the password field is left blank or passwords and confirmations are not the same, return apology.
        if not request.form.get("password") or request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide password and matching confirmation", 403)
        else:
            # Assign username to a variable.
            username = request.form.get("username")
            # Assign password to a variable.
            password = request.form.get("password")
            # Check to make sure password contains special characters.
            if len(password) < 8:
                return apology("password must be at least 8 characters", 403)
            # Hash the user's password for security.
            password_hash = generate_password_hash(request.form.get("password"))
            # Insert new user row into users table.
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hash)",
                       username=username, password_hash=password_hash)
            # Redirect user to homepage when finished.
            return redirect("/")
    # Otherwise, we have a GET request, so we send the user to the register page to register their information.
    else:
        return render_template("register.html")

# Lets the user sell stock shares.
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # Identify the user.
    user_id = session["user_id"]
    # Amount of shares for a given stock this user has.
    shares_sum = 0
    # User simply accesses the sell page to look up and sell stocks contained in their portfolio.
    if request.method == "GET":
        stocks_list = []
        # Get all symbol values with the user's id.
        user_stock_symbols = db.execute("SELECT symbol FROM stocks WHERE user_id=:user_id", user_id=user_id)
        # Get only the values of each list entry, not the keys. Used with help from:
        # https://www.geeksforgeeks.org/python-get-values-of-particular-key-in-list-of-dictionaries/
        values = [sub['symbol'] for sub in user_stock_symbols]
        # Get list of all stock symbols owned by user.
        for symbol in values:
            print(values)
            if not symbol in stocks_list:
                stocks_list.append(symbol)
        return render_template("sell.html", stocks_list=stocks_list)
    # User reached route via POST (as by submitting a form via POST), and entered some information.
    else:
        # Get symbol of stock from submitted form.
        symbol = request.form.get("symbol")
        # Get number of shares entered by the user.
        shares = int(request.form.get("shares"))
        # Make shares number negative to discern between a bought and sold transaction inside the database.
        sold_shares = -shares
        # Get all symbol values with the user's id.
        user_stock_symbols = db.execute("SELECT symbol FROM stocks WHERE user_id=:user_id", user_id=user_id)
        # Apology: check that user owns this stock.
        # Get only the values of each list entry, not the keys. Used with help from:
        # https://www.geeksforgeeks.org/python-get-values-of-particular-key-in-list-of-dictionaries/
        values = [sub['symbol'] for sub in user_stock_symbols]
        if symbol not in values:
            return apology("stock not owned!", 403)
        # Apology: check that user is not trying to sell more shares than they own for that stock.
        user_stock_symbol_shares = db.execute("SELECT shares FROM stocks WHERE user_id=:user_id AND symbol=:symbol",
                                             user_id=user_id, symbol=symbol)
        # Transform dict values (as this is the format received from db.execute) in "shares" column to int from all_shares.
        for share in user_stock_symbol_shares:
            shares_sum += int(share.get('shares'))
        if shares > shares_sum:
            return apology("you don't have that many shares to sell!", 403)
        # Look up real time stock information via helpers.py lookup().
        stock_info = lookup(symbol)
        # Get the stock's information to store in our stocks table.
        stock_info_list = []
        for value in stock_info.values():
            stock_info_list.append(value)
        # Give each index their appropriate declarations so we can display properly in HTML.
        name = stock_info_list[0]
        # Format the price using helpers.usd() to show its currency.
        price = usd(stock_info_list[1])
        # Create an unformatted_price to multiply by the requested shares to sell.
        unformatted_price = stock_info_list[1]
        sell_price = shares * float(unformatted_price)
        # Subtract the sell_price from our total DB user's cash.
        cash = db.execute("SELECT cash FROM users WHERE id=:user_id",
                          user_id=user_id)
        cash_balance = cash[0]
        # Get new cash total after sale.
        new_cash_total = cash_balance['cash'] + sell_price
        # Get time transaction was made.
        transacted = datetime.now()
        # Change amount of user's cash in users after transaction.
        db.execute("UPDATE users SET cash=:new_cash_total WHERE id=:user_id",
                   user_id=user_id, new_cash_total=new_cash_total)
        # Record the sell, using negative values in the db to indicate it was a sale and not a buy.
        db.execute("INSERT INTO stocks (user_id, symbol, name, shares, price, transacted) VALUES (:user_id, :symbol, :name, :sold_shares, :price, :transacted)",
                    user_id=user_id, symbol=symbol, name=name, sold_shares=sold_shares, price=price, transacted=transacted)
        # Return HTML to the user.
        return index()

# Handles errors.
def errorhandler(e):
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listens for errors.
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
