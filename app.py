from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import smtplib
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    complaint = db.Column(db.Text, nullable=False)
    submitted_on = db.Column(db.String(50), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/client')
def client():
    return render_template('client.html')

@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        account_number = request.form['account']
        complaint_text = request.form['complaint']

        if not all([name, email, account_number, complaint_text]):
            flash("All fields are required!", "error")
            return redirect(url_for('complaint'))

        new_complaint = Complaint(
            name=name,
            email=email,
            account_number=account_number,
            complaint=complaint_text,
            submitted_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(new_complaint)
        db.session.commit()
        flash("Complaint submitted successfully!", "success")
        return redirect(url_for('complaint'))

    return render_template('complaint.html')

@app.route('/view_complaints')
def view_complaints():
    complaints = Complaint.query.order_by(Complaint.submitted_on.desc()).all()
    return render_template('view_complaints.html', complaints=complaints)

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        account_number = request.form['account_number']
        amount = request.form['amount']
        note = request.form.get('note', '')

        if not account_number or not amount:
            flash("Account number and amount are required!", "error")
            return redirect(url_for('deposit'))

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid amount entered!", "error")
            return redirect(url_for('deposit'))

        transaction = Transaction(
            account_number=account_number,
            amount=amount,
            type='deposit',
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=note
        )
        db.session.add(transaction)
        db.session.commit()
        flash(f"\u20B9{amount} deposited successfully to account {account_number}.", "success")
        return redirect(url_for('deposit'))

    return render_template('deposit.html')

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if request.method == 'POST':
        account_number = request.form['account_number']
        amount = request.form['amount']

        if not account_number or not amount:
            flash("Account number and amount are required!", "error")
            return redirect(url_for('withdraw'))

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid amount entered!", "error")
            return redirect(url_for('withdraw'))

        balance = get_balance(account_number)
        if amount > balance:
            flash("Insufficient funds for withdrawal!", "error")
            return redirect(url_for('withdraw'))

        transaction = Transaction(
            account_number=account_number,
            amount=-amount,
            type='withdraw',
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=''
        )
        db.session.add(transaction)
        db.session.commit()

        flash(f"\u20B9{amount} withdrawn successfully from account {account_number}.", "success")
        return redirect(url_for('withdraw'))

    return render_template('withdraw.html')

def get_balance(account_number):
    result = db.session.query(db.func.sum(Transaction.amount)).filter_by(account_number=account_number).scalar()
    return result if result else 0

@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('type', '', type=str)

    query = Transaction.query
    if filter_type:
        query = query.filter_by(type=filter_type)

    transactions = query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=10)
    return render_template('history.html', transactions=transactions.items, total_pages=transactions.pages, current_page=page, filter_type=filter_type)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password(password, user.password):
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "error")

    return render_template('login.html')

def check_password(input_password, stored_password):
    return hashlib.sha256(input_password.encode()).hexdigest() == stored_password

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        send_email(name, email, message)
        return redirect(url_for('thank_you'))
    return render_template('contact.html')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

def send_email(name, email, message):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your_email@gmail.com', 'your_password')
        subject = 'New Contact Form Submission'
        body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
        email_message = f"Subject: {subject}\n\n{body}"
        server.sendmail('your_email@gmail.com', 'receiver_email@example.com', email_message)
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

def create_tables():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run(debug=True)
