from flask import Flask, render_template, request, flash, redirect, url_for, session, logging, jsonify, Response
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, TextAreaField, IntegerField, validators
from wtforms.validators import DataRequired
from passlib.hash import sha256_crypt
from functools import wraps
import timeago
import datetime
from wtforms.fields.html5 import EmailField
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_mail import Mail, Message
import plotly.graph_objects as go

app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('config.py')

mysql = MySQL(app)
mail = Mail(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


class SignUpForm(Form):
    first_name = StringField('First Name', [validators.Length(min=1, max=100)])
    last_name = StringField('Last Name', [validators.Length(min=1, max=100)])
    email = EmailField('Email address', [
                       validators.DataRequired(), validators.Email()])
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('addTransactions'))
    form = SignUpForm(request.form)
    if request.method == 'POST' and form.validate():
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE email=%s", [email])
        if result > 0:
            flash('The entered email address has already been taken.Please try using or creating another one.', 'info')
            return redirect(url_for('signup'))
        else:
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
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('addTransactions'))
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
            "INSERT INTO transactions(user_id, amount, description,category) VALUES(%s, %s, %s, %s)", (session['userID'], amount, description, category))

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
                if datetime.datetime.now() - transaction['date'] < datetime.timedelta(days=0.5):
                    transaction['date'] = timeago.format(
                        transaction['date'], datetime.datetime.now())
                else:
                    transaction['date'] = transaction['date'].strftime(
                        '%d %B, %Y')
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
            for transaction in transactions:
                transaction['date'] = transaction['date'].strftime(
                    '%d %B, %Y')
            return render_template('transactionHistory.html', totalExpenses=totalExpenses, transactions=transactions)
        else:
            cur.execute(f"SELECT MONTHNAME('0000-{month}-00')")
            data = cur.fetchone()
            if month != "00":
                monthName = data[f'MONTHNAME(\'0000-{month}-00\')']
                msg = f"No Transactions Found For {monthName}, {year}"
            else:
                msg = f"No Transactions Found For {year}"
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
            for transaction in transactions:
                transaction['date'] = transaction['date'].strftime(
                    '%d %B, %Y')
            return render_template('transactionHistory.html', totalExpenses=totalExpenses, transactions=transactions)
        else:
            flash('No Transactions Found', 'success')
            return redirect(url_for('addTransactions'))
        # Close connection
        cur.close()


class TransactionForm(Form):
    amount = IntegerField('Amount', validators=[DataRequired()])
    description = StringField('Description', [validators.Length(min=1)])

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


@app.route('/editCurrentMonthTransaction/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def editCurrentMonthTransaction(id):
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

        return redirect(url_for('addTransactions'))

    return render_template('editTransaction.html', form=form)

# Delete transaction
@app.route('/deleteCurrentMonthTransaction/<string:id>', methods=['POST'])
@is_logged_in
def deleteCurrentMonthTransaction(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM transactions WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Transaction Deleted', 'success')

    return redirect(url_for('addTransactions'))


class RequestResetForm(Form):
    email = EmailField('Email address', [
                       validators.DataRequired(), validators.Email()])


@app.route("/reset_request", methods=['GET', 'POST'])
def reset_request():
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('index'))
    form = RequestResetForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        cur = mysql.connection.cursor()
        result = cur.execute(
            "SELECT id,username,email FROM users WHERE email = %s", [email])
        if result == 0:
            flash(
                'There is no account with that email. You must register first.', 'warning')
            return redirect(url_for('signup'))
        else:
            data = cur.fetchone()
            user_id = data['id']
            user_email = data['email']
            cur.close()
            s = Serializer(app.config['SECRET_KEY'], 1800)
            token = s.dumps({'user_id': user_id}).decode('utf-8')
            msg = Message('Password Reset Request',
                          sender='noreply@demo.com', recipients=[user_email])
            msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make password reset request then simply ignore this email and no changes will be made.
Note:This link is valid only for 30 mins from the time you requested a password change request.
'''
            mail.send(msg)
            flash(
                'An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('login'))
    return render_template('reset_request.html', form=form)


class ResetPasswordForm(Form):
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('index'))
    s = Serializer(app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token)['user_id']
    except:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE id = %s", [user_id])
    data = cur.fetchone()
    cur.close()
    user_id = data['id']
    form = ResetPasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        password = sha256_crypt.encrypt(str(form.password.data))
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET password = %s WHERE id = %s", (password, user_id))
        mysql.connection.commit()
        cur.close()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

# Category Wise Pie Chart For Current Year As Percentage #
@app.route('/category')
def createBarCharts():
    cur = mysql.connection.cursor()
    result = cur.execute(
        f"SELECT Sum(amount) AS amount, category FROM transactions WHERE YEAR(date) = YEAR(CURRENT_DATE()) AND user_id = {session['userID']} GROUP BY category ORDER BY category")
    if result > 0:
        transactions = cur.fetchall()
        values = []
        labels = []
        for transaction in transactions:
            values.append(transaction['amount'])
            labels.append(transaction['category'])

        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        fig.update_traces(textinfo='label+value', hoverinfo='percent')
        fig.update_layout(
            title_text='Category Wise Pie Chart For Current Year')
        fig.show()
    cur.close()
    return redirect(url_for('addTransactions'))

# Comparison Between Current and Previous Year #
@app.route('/yearly_bar')
def yearlyBar():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('01', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        a1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('01', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        a2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('02', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        b1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('02', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        b2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('03', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        c1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('03', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        c2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('04', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        d1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('04', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        d2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('05', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        e1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('05', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        e2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('06', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        f1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('06', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        f2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('07', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        g1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('07', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        g2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('08', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        h1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('08', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        h2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('09', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        i1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('09', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        i2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('10', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        j1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('10', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        j2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('11', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        k1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('11', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        k2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ('12', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        l1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE MONTH(date) = %s  AND YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ('12', [
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        l2 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE  YEAR(date) = YEAR(CURRENT_DATE())  AND user_id = %s", ([
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        m1 = data['Sum(amount)']
    result = cur.execute("SELECT Sum(amount) FROM transactions WHERE YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 YEAR))  AND user_id = %s", ([
        session['userID']]))
    if result > 0:
        data = cur.fetchone()
        m2 = data['Sum(amount)']

    year = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June',
            'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec', 'Total']
    fig = go.Figure(data=[
        go.Bar(name='Last Year', x=year, y=[
               a2, b2, c2, d2, e2, f2, g2, h2, i2, j2, k2, l2, m2]),
        go.Bar(name='This Year', x=year, y=[
               a1, b1, c1, d1, e1, f1, g1, h1, i1, j1, k1, l1, m1])
    ])
    fig.update_layout(
        barmode='group', title_text='Comparison Between This Year and Last Year')
    fig.show()
    return redirect(url_for('addTransactions'))

# Current Year Month Wise #
@app.route('/monthly_bar')
def monthlyBar():
    cur = mysql.connection.cursor()
    result = cur.execute(
        f"SELECT sum(amount) as amount, month(date) FROM transactions WHERE YEAR(date) = YEAR(CURRENT_DATE()) AND user_id = {session['userID']} GROUP BY MONTH(date) ORDER BY MONTH(date)")
    if result > 0:
        transactions = cur.fetchall()
        year = []
        value = [] 
        for transaction in transactions:
            year.append(transaction['month(date)'])
            value.append(transaction['amount'])

        fig = go.Figure([go.Bar(x=year, y=value)])
        fig.update_layout(title_text='Monthly Bar Chart For Current Year')
        fig.show()
    cur.close()
    return redirect(url_for('addTransactions'))

if __name__ == '__main__':
    app.run(debug=True)
