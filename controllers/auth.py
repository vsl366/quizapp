from flask import Flask, Blueprint,render_template, request, redirect, url_for, flash, session
import sqlite3
from functools import wraps

DATABASE = "quiz.db"


auth_bp = Blueprint('auth', __name__)


# Login required decorator with role check
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))  # Redirect to login if not logged in

            # Check if user has the correct role
            if role and session.get('role') != role:
                return redirect(url_for('auth.login'))  # Redirect if user doesn't have the correct role

            return f(*args, **kwargs)

        return decorated_function
    return decorator


#Routes
@auth_bp.route('/')
def home():
    return redirect(url_for('auth.login'))  # Redirect to login page


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form  # Check if the admin checkbox is checked
        action = request.form.get('action')  # Determine which button was pressed (Login or Sign Up)

        if action == 'login':  # Handle login action
            if not username or not password:
                flash("Username and Password are required for login.", "error")
                return render_template('login.html')  # Re-render the login page with an error message

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            if is_admin:
                cursor.execute('SELECT * FROM users WHERE username = ? AND password = ? AND role = ?',
                               (username, password, 'admin'))
                admin = cursor.fetchone()
                if admin:
                    session['user_id'] = admin[0]
                    session['role'] = 'admin'  # Store the role in the session
                    conn.close()
                    return redirect(url_for('admin.admin'))
                else:
                    flash("Invalid admin credentials.", "error")
            else:
                cursor.execute('SELECT * FROM users WHERE username = ? AND password = ? AND role = ?',
                               (username, password, 'student'))
                student = cursor.fetchone()
                if student:
                    session['user_id'] = student[0]
                    session['role'] = 'student'  # Store the role in the session
                    conn.close()
                    return redirect(url_for('student.student_page'))
                else:
                    flash("Invalid student credentials.", "error")

            conn.close()

        elif action == 'signup':  # Redirect to the registration page when "Sign Up" is clicked
            return redirect(url_for('auth.register'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        fullname = request.form.get('fullname')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')

        if not username or not password or not fullname or not qualification or not dob:
            flash("All fields are required.", "error")
            return render_template('register.html')

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute('''INSERT INTO users (username, password, fullname, qualification, dob, role, score) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (username, password, fullname, qualification, dob, 'student', 0))
            conn.commit()
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for('auth.login'))  # Redirect to login page after successful registration

        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose another.", "error")

        conn.close()

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)  # Remove role from session
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
