from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, TextAreaField, IntegerField, validators
from wtforms.validators import DataRequired
from passlib.hash import sha256_crypt
from functools import wraps
import timeago
import datetime

app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('config.py')

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


class SignUpForm(Form):
    first_name = StringField('First Name', [validators.Length(min=1, max=100)])
    last_name = StringField('Last Name', [validators.Length(min=1, max=100)])
    email = StringField('Email', [validators.Length(min=6, max=100)])
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm(request.form)
    if request.method == 'POST' and form.validate():
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(first_name, last_name, email, username, password) VALUES(%s, %s, %s, %s, %s)",
                    (first_name, last_name, email, username, password))
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    return render_template('signUp.html', form=form)


class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
    ])


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password_input = form.password.data

        cur = mysql.connection.cursor()

        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            userID = data['id']
            password = data['password']
            role = data['role']

            if sha256_crypt.verify(password_input, password):
                session['logged_in'] = True
                session['username'] = username
                session['role'] = role
                session['userID'] = userID
                flash('You are now logged in', 'success')
                return redirect(url_for('addTransactions'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', form=form, error=error)

            cur.close()

        else:
            error = 'Username not found'
            return render_template('login.html', form=form, error=error)

    return render_template('login.html', form=form)


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please login', 'info')
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Add Transactions
@app.route('/addTransactions', methods=['GET', 'POST'])
@is_logged_in
def addTransactions():
    if request.method == 'POST':
        amount = request.form['amount']
        description = request.form['description']
        category = request.form['category']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute(
            "INSERT INTO transactions(user_id, amount, description,category) VALUES(%s, %s, %s, %s)", (session['userID'], amount, description,category))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Transaction Successfully Recorded', 'success')

        return redirect(url_for('addTransactions'))

    else:
        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT SUM(amount) FROM transactions WHERE MONTH(date) = MONTH(CURRENT_DATE()) AND YEAR(date) = YEAR(CURRENT_DATE()) AND user_id = %s", [session['userID']])

        data = cur.fetchone()
        totalExpenses = data['SUM(amount)']

        # get the month's transactions made by a particular user
        result = cur.execute(
            "SELECT * FROM transactions WHERE MONTH(date) = MONTH(CURRENT_DATE()) AND YEAR(date) = YEAR(CURRENT_DATE()) AND user_id = %s ORDER BY date DESC", [
                session['userID']]
        )

        if result > 0:
            transactions = cur.fetchall()
            for transaction in transactions:
                transaction['date'] = timeago.format(
                    transaction['date'], datetime.datetime.now())
            return render_template('addTransactions.html', totalExpenses=totalExpenses, transactions=transactions)
        else:
            return render_template('addTransactions.html', result=result)

        # close the connections
        cur.close()

    return render_template('addTransactions.html')
    

@app.route('/transactionHistory', methods=['GET', 'POST'])
@is_logged_in
def transactionHistory():

    if request.method == 'POST':
        month = request.form['month']
        year = request.form['year']
        # Create cursor
        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = %s", [session['userID']])

        data = cur.fetchone()
        totalExpenses = data['SUM(amount)']

        if month == "00":
            cur.execute(
                f"SELECT SUM(amount) FROM transactions WHERE YEAR(date) = YEAR('{year}-00-00') AND user_id = {session['userID']}")

            data = cur.fetchone()
            totalExpenses = data['SUM(amount)']

            result = cur.execute(
                f"SELECT * FROM transactions WHERE YEAR(date) = YEAR('{year}-00-00') AND user_id = {session['userID']} ORDER BY date DESC")
        else:

            cur.execute(
                f"SELECT SUM(amount) FROM transactions WHERE MONTH(date) = MONTH('0000-{month}-00') AND YEAR(date) = YEAR('{year}-00-00') AND user_id = {session['userID']}")

            data = cur.fetchone()
            totalExpenses = data['SUM(amount)']

            result = cur.execute(
                f"SELECT * FROM transactions WHERE MONTH(date) = MONTH('0000-{month}-00') AND YEAR(date) = YEAR('{year}-00-00') AND user_id = {session['userID']} ORDER BY date DESC")

        if result > 0:
            transactions = cur.fetchall()
            return render_template('transactionHistory.html', totalExpenses=totalExpenses, transactions=transactions)
        else:
            cur.execute(f"SELECT MONTHNAME('0000-{month}-00')")
            data = cur.fetchone()
            monthName = data[f'MONTHNAME(\'0000-{month}-00\')']
            msg = f"No Transactions Found For {monthName}, {year}"
            return render_template('transactionHistory.html', result=result, msg=msg)
        # Close connection
        cur.close()
    else:
        # Create cursor
        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = %s", [session['userID']])

        data = cur.fetchone()
        totalExpenses = data['SUM(amount)']

        # Get Latest Transactions made by a particular user
        result = cur.execute(
            "SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC", [
                session['userID']]
        )

        if result > 0:
            transactions = cur.fetchall()
            return render_template('transactionHistory.html', totalExpenses=totalExpenses, transactions=transactions)
        else:
            flash('No Transactions Found', 'success')
            return redirect(url_for('addTransactions'))
        # Close connection
        cur.close()


class TransactionForm(Form):
    amount = IntegerField('Amount', validators=[DataRequired()])
    description = StringField('Description', [validators.Length(min=1)])

# Edit Transactions
@app.route('/editTransaction', methods=['GET', 'POST'])
@is_logged_in
def editTransactions():
    form = TransactionForm(request.form)
    if request.method == 'POST' and form.validate():
        amount = form.amount.data
        description = form.description.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute(
            "INSERT INTO transactions(user_id, amount, description) VALUES(%s, %s, %s)", (session['userID'], amount, description))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Transaction Successfully Recorded', 'success')

        return redirect(url_for('transactionHistory'))

    return render_template('editTransaction.html', form=form)

# Edit transaction
@app.route('/editTransaction/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def editTransaction(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get transaction by id
    cur.execute("SELECT * FROM transactions WHERE id = %s", [id])

    transaction = cur.fetchone()
    cur.close()
    # Get form
    form = TransactionForm(request.form)

    # Populate transaction form fields
    form.amount.data = transaction['amount']
    form.description.data = transaction['description']

    if request.method == 'POST' and form.validate():
        amount = request.form['amount']
        description = request.form['description']

        # Create Cursor
        cur = mysql.connection.cursor()
        # Execute
        cur.execute("UPDATE transactions SET amount=%s, description=%s WHERE id = %s",
                    (amount, description, id))
        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Transaction Updated', 'success')

        return redirect(url_for('transactionHistory'))

    return render_template('editTransaction.html', form=form)

# Delete transaction
@app.route('/deleteTransaction/<string:id>', methods=['POST'])
@is_logged_in
def deleteTransaction(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM transactions WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Transaction Deleted', 'success')

    return redirect(url_for('transactionHistory'))


if __name__ == '__main__':
    app.run(debug=True)
