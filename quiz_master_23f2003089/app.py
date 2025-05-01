from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import sqlite3
import datetime
import random
import os
from functools import wraps
app = Flask(__name__)
app.secret_key = "secret_key"  # Used for flashing messages


DATABASE = "quiz.db"
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # ------------------ Create Tables ------------------ #
        cursor.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            qualification TEXT NOT NULL, -- Options: 10th, 12th, Bachelors, Masters, Doctoral
            dob DATE,
            role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
            score INTEGER DEFAULT 0
        )''')

        cursor.execute('''CREATE TABLE subject (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )''')

        cursor.execute('''CREATE TABLE chapter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            subject_id INTEGER,
            FOREIGN KEY (subject_id) REFERENCES subject(id)
        )''')

        cursor.execute('''CREATE TABLE quiz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_name TEXT NOT NULL,
            chapter_id INTEGER,
            date DATE NOT NULL,
            duration INTEGER NOT NULL, -- Duration in minutes
            remark TEXT,
            no_of_qns INTEGER NOT NULL,
            FOREIGN KEY (chapter_id) REFERENCES chapter(id)
        )''')

        cursor.execute('''CREATE TABLE question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question_text TEXT NOT NULL,
            option_1 TEXT NOT NULL,
            option_2 TEXT NOT NULL,
            option_3 TEXT NOT NULL,
            option_4 TEXT NOT NULL,
            correct_option INTEGER NOT NULL,
            FOREIGN KEY (quiz_id) REFERENCES quiz(id)
        )''')

        cursor.execute('''CREATE TABLE scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_user_score INTEGER NOT NULL,
            FOREIGN KEY (quiz_id) REFERENCES quiz(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # ------------------ Original Inserts ------------------ #
        # Insert sample admin user
        cursor.execute('''INSERT INTO users (username, password, fullname, qualification, dob, role, score) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       ("admin", "admin123", "Admin User", "Masters", "1990-01-01", "admin", 0))
        
        # Insert sample subjects
        subjects = [
            ("Mathematics", "A subject that deals with numbers, shapes, and patterns"),
            ("Physics", "The study of matter, energy, and the forces of nature"),
            ("Chemistry", "The study of substances and their properties and reactions"),
            ("Biology", "The study of living organisms and their interactions with the environment")
        ]
        for subj in subjects:
            cursor.execute("INSERT INTO subject (name, description) VALUES (?, ?)", subj)
        
        # Insert chapters for these subjects
        chapters = [
            ("Algebra", "A branch of mathematics dealing with symbols and rules.", 1),
            ("Geometry", "The branch of mathematics concerned with spatial properties.", 1),
            ("Calculus", "The branch of mathematics that studies change.", 1),
            ("Mechanics", "The study of motion and forces.", 2),
            ("Thermodynamics", "The branch of physics concerned with heat.", 2),
            ("Organic Chemistry", "The study of organic compounds.", 3),
            ("Inorganic Chemistry", "The study of inorganic compounds.", 3),
            ("Ecology", "The study of ecosystems.", 4),
            ("Genetics", "The study of heredity.", 4)
        ]
        for chap in chapters:
            cursor.execute("INSERT INTO chapter (name, description, subject_id) VALUES (?, ?, ?)", chap)

        # Insert quizzes with dates in the past (closed quizzes)
        quizzes = [
            ("Basic Maths", 1, "2025-01-01", 30, "Algebra Quiz", 5),
            ("Newtonian Mechanics", 4, "2025-01-02", 2, "Mechanics Quiz", 5),
            ("Quantum Theory", 4, "2025-01-20", 30, "Quiz on quantum concepts", 5),
            ("Ancient Civilizations", 5, "2025-01-15", 20, "History quiz on ancient times", 5),  # We'll update this chapter_id later
            ("Calculus Introduction", 3, "2025-01-10", 25, "Introductory calculus", 5)
        ]
        quiz_ids = {}
        for quiz in quizzes:
            cursor.execute('''INSERT INTO quiz (quiz_name, chapter_id, date, duration, remark, no_of_qns) 
                              VALUES (?, ?, ?, ?, ?, ?)''', quiz)
            quiz_ids[quiz[0]] = cursor.lastrowid

        # Insert questions for each quiz – ensure exactly 5 questions per quiz.
        # Basic Maths questions (5 questions)
        basic_math_questions = [
            ("What is 2 + 2?", "3", "4", "5", "6", 2),
            ("Solve for x: 2x = 6", "1", "2", "3", "4", 3),
            ("What is 10 - 3?", "7", "8", "6", "5", 1),
            ("What is 3 + 5?", "7", "8", "9", "10", 2),
            ("What is 2 * 3?", "5", "6", "7", "8", 2)
        ]
        for q in basic_math_questions:
            cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Basic Maths"], *q))

        # Newtonian Mechanics questions (5 questions)
        newtonian_questions = [
            ("What is Newton's second law?", "F = ma", "F = mv", "F = mg", "F = ma^2", 1),
            ("What is the unit of force?", "Kilogram", "Newton", "Joule", "Meter", 2),
            ("What is the formula for momentum?", "mass * velocity", "mass * acceleration", "force * time", "mass / velocity", 1),
            ("What unit is used to measure energy?", "Newton", "Joule", "Watt", "Pascal", 2),
            ("Which law explains inertia?", "Newton's first law", "Newton's second law", "Newton's third law", "Hooke's law", 1)
        ]
        for q in newtonian_questions:
            cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Newtonian Mechanics"], *q))

        # Quantum Theory questions (5 questions)
        quantum_questions = [
            ("What does the term 'quantum' refer to?", "A discrete quantity", "A continuous wave", "An atom", "A particle accelerator", 1),
            ("Who is considered the father of quantum mechanics?", "Albert Einstein", "Niels Bohr", "Max Planck", "Erwin Schrödinger", 3),
            ("What is the smallest unit of energy called?", "Quantum", "Photon", "Electron", "Nucleus", 1),
            ("Which scientist introduced the concept of quantization of energy?", "Max Planck", "Isaac Newton", "Galileo Galilei", "Albert Einstein", 1),
            ("What phenomenon does quantum tunneling describe?", "Particles passing through barriers", "Light bending around corners", "Energy loss in circuits", "Temperature change", 1)
        ]
        for q in quantum_questions:
            cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Quantum Theory"], *q))

        # Ancient Civilizations questions (5 questions)
        ancient_questions = [
            ("Which civilization built the pyramids?", "Romans", "Egyptians", "Greeks", "Mayans", 2),
            ("Which ancient civilization is known for its philosophy?", "Egyptians", "Greeks", "Romans", "Vikings", 2),
            ("Which ancient civilization developed cuneiform writing?", "Sumerians", "Egyptians", "Romans", "Mayans", 1),
            ("Which empire was ruled by Julius Caesar?", "Roman", "Greek", "Egyptian", "Persian", 1),
            ("Which ancient civilization built the Parthenon?", "Egyptians", "Romans", "Greeks", "Chinese", 3)
        ]
        # IMPORTANT: We'll update the chapter assignment for this quiz below.
        cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Ancient Civilizations"], *ancient_questions[0]))
        cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Ancient Civilizations"], *ancient_questions[1]))
        cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Ancient Civilizations"], *ancient_questions[2]))
        cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Ancient Civilizations"], *ancient_questions[3]))
        cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Ancient Civilizations"], *ancient_questions[4]))

        # Calculus Introduction questions (5 questions)
        calculus_questions = [
            ("What is the derivative of x^2?", "x", "2x", "x^2", "2", 2),
            ("What is the integral of 1/x dx?", "ln|x| + C", "1/(x^2)", "e^x + C", "x + C", 1),
            ("What is the derivative of sin(x)?", "cos(x)", "-cos(x)", "sin(x)", "-sin(x)", 1),
            ("What is the derivative of cos(x)?", "-sin(x)", "sin(x)", "cos(x)", "-cos(x)", 1),
            ("What is the limit of 1/x as x approaches infinity?", "0", "1", "Infinity", "Does not exist", 1)
        ]
        for q in calculus_questions:
            cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', (quiz_ids["Calculus Introduction"], *q))

        # ------------------ Additional Inserts ------------------ #
        # Additional Users (students)
        students = [
            ("student1", "pass1", "Alice Smith", "Bachelors", "2000-05-10", "student", 0),
            ("student2", "pass2", "Bob Johnson", "Masters", "1999-08-22", "student", 0),
            ("student3", "pass3", "Charlie Davis", "12th", "2003-12-12", "student", 0),
            ("student4", "pass4", "Diana Evans", "Bachelors", "2001-03-03", "student", 0),
            ("student5", "pass5", "Ethan Brown", "10th", "2005-07-07", "student", 0),
            ("student6", "pass6", "Fiona Green", "Doctoral", "1995-11-30", "student", 0)
        ]
        for s in students:
            cursor.execute('''INSERT INTO users (username, password, fullname, qualification, dob, role, score)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', s)

        # Additional Subjects (History, Geography, Computer Science)
        extra_subjects = [
            ("History", "The study of past events."),
            ("Geography", "The study of Earth's physical features and human activity."),
            ("Computer Science", "The study of computation, automation, and information.")
        ]
        for subj in extra_subjects:
            cursor.execute("INSERT INTO subject (name, description) VALUES (?, ?)", subj)
        
        # Additional Chapters for new subjects
        extra_chapters = [
            ("Ancient History", "Study of ancient civilizations.", 5),
            ("Modern History", "Study of recent historical events.", 5),
            ("Physical Geography", "Study of natural environment and landforms.", 6),
            ("Human Geography", "Study of human populations and cultures.", 6),
            ("Programming", "Basics of computer programming.", 7),
            ("Data Structures", "Study of organizing data efficiently.", 7)
        ]
        for chap in extra_chapters:
            cursor.execute("INSERT INTO chapter (name, description, subject_id) VALUES (?, ?, ?)", chap)
        
        # Additional quiz for History (closed quiz)
        history_questions = [
            ("Which civilization built the pyramids?", "Romans", "Egyptians", "Greeks", "Mayans", 2),
            ("Which ancient civilization is known for its philosophy?", "Egyptians", "Greeks", "Romans", "Vikings", 2),
            ("Which civilization built the Colosseum?", "Egyptians", "Mesopotamians", "Romans", "Indians", 3),
            ("The Code of Hammurabi comes from which civilization?", "Babylonian", "Greek", "Roman", "Egyptian", 1),
            ("Which river was central to ancient Egyptian civilization?", "Nile", "Tigris", "Euphrates", "Indus", 1)
        ]
        # IMPORTANT: Use the extra chapter "Ancient History" instead of chapter id 5.
        cursor.execute('''INSERT INTO quiz (quiz_name, chapter_id, date, duration, remark, no_of_qns)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       ("Ancient Civilizations", 10, "2025-01-15", 20, "History quiz on ancient times", len(history_questions)))
        hist_quiz_id = cursor.lastrowid
        for q in history_questions:
            cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', (hist_quiz_id, *q))
        
        # ------------------ Sample Scores ------------------ #
        # Insert sample scores only for quizzes that have already "occurred" (date <= '2025-04-30')
        cursor.execute("SELECT id, no_of_qns, date FROM quiz WHERE date <= '2025-04-30'")
        closed_quizzes = cursor.fetchall()
        cursor.execute("SELECT id FROM users WHERE role = 'student'")
        all_students = cursor.fetchall()

        # For each closed quiz, for each student, randomly decide if they attempted the quiz (e.g. 70% chance)
        for quiz in closed_quizzes:
            quiz_id = quiz[0]
            max_qns = quiz[1]
            for student in all_students:
                if random.random() < 0.7:  # 70% chance that the student attempted this quiz
                    score = random.randint(2, max_qns)
                    cursor.execute("INSERT INTO scores (quiz_id, user_id, total_user_score) VALUES (?, ?, ?)",
                                   (quiz_id, student[0], score))
        
        # Update users' cumulative score based on inserted scores
        cursor.execute("""
            UPDATE users
            SET score = (SELECT IFNULL(SUM(total_user_score), 0)
                         FROM scores
                         WHERE scores.user_id = users.id)
        """)

        # ------------------ Upcoming Quizzes ------------------ #
        # Add extra quizzes that are scheduled after April 30, 2025 (no sample scores inserted)
        upcoming_quiz_questions = [
            ("What is the capital of France?", "Paris", "London", "Berlin", "Madrid", 1),
            ("Which planet is known as the Red Planet?", "Earth", "Mars", "Jupiter", "Venus", 2),
            ("What is 10 + 15?", "20", "25", "30", "35", 2),
            ("Which element has the chemical symbol 'O'?", "Gold", "Oxygen", "Silver", "Hydrogen", 2),
            ("Who wrote 'Hamlet'?", "Shakespeare", "Dickens", "Hemingway", "Tolkien", 1)
        ]
        cursor.execute('''INSERT INTO quiz (quiz_name, chapter_id, date, duration, remark, no_of_qns)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       ("Upcoming Quiz 1", 1, "2025-05-10", 30, "An upcoming quiz", len(upcoming_quiz_questions)))
        upcoming_quiz_id = cursor.lastrowid
        for q in upcoming_quiz_questions:
            cursor.execute('''INSERT INTO question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_option)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', (upcoming_quiz_id, *q))
        
        conn.commit()
        conn.close()
# Initialize the database
init_db()


# Login required decorator with role check
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))  # Redirect to login if not logged in

            # Check if user has the correct role
            if role and session.get('role') != role:
                return redirect(url_for('login'))  # Redirect if user doesn't have the correct role

            return f(*args, **kwargs)

        return decorated_function
    return decorator


#Routes
@app.route('/')
def home():
    return redirect(url_for('login'))  # Redirect to login page


@app.route('/login', methods=['GET', 'POST'])
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
                    return redirect(url_for('admin'))
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
                    return redirect(url_for('student_page'))
                else:
                    flash("Invalid student credentials.", "error")

            conn.close()

        elif action == 'signup':  # Redirect to the registration page when "Sign Up" is clicked
            return redirect(url_for('register'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('login'))  # Redirect to login page after successful registration

        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose another.", "error")

        conn.close()

    return render_template('register.html')


@app.route('/admin', methods=['GET'])
@login_required(role='admin')
def admin():
    # Get the search query from the URL parameter
    search_query = request.args.get('search', '')  
    
    # Establish a connection to the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if search_query:
        # Modify the query to include a search filter for name or description
        query = '''
        SELECT s.id, s.name, s.description, COUNT(c.id) AS chapter_count
        FROM subject s
        LEFT JOIN chapter c ON s.id = c.subject_id
        WHERE s.name LIKE ? OR s.description LIKE ?
        OR c.name LIKE ? OR c.description LIKE ?
        GROUP BY s.id
        '''
        cursor.execute(query, (f'%{search_query}%', f'%{search_query}%',f'%{search_query}%', f'%{search_query}%'))  # Using LIKE to match the search term
    else:
        # If no search query, fetch all subjects without filtering
        query = '''
        SELECT s.id, s.name, s.description, COUNT(c.id) AS chapter_count
        FROM subject s
        LEFT JOIN chapter c ON s.id = c.subject_id
        GROUP BY s.id
        '''
        cursor.execute(query)
    
    subjects = cursor.fetchall()  # Fetch all the subjects (either filtered or all)
    conn.close()
    
    print(subjects)  # For debugging purposes, you can see the subjects in the console
    
    return render_template('admin.html', subjects=subjects)


@app.route('/student')
@login_required(role='student')
def student_page():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enables dict-like access
    cursor = conn.cursor()
    
    # Get student score and full name
    cursor.execute('SELECT score, fullname FROM users WHERE id = ?', (session['user_id'],))
    user_row = cursor.fetchone()
    score = user_row['score']
    student_name = user_row['fullname']
    
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # Get search query from user input
    search_query = request.args.get('search', '').strip().lower()

    # Fetch all unattempted quizzes
    query_all_quizzes = '''
    SELECT quiz.id, quiz.quiz_name, quiz.date, quiz.duration, quiz.no_of_qns
    FROM quiz
    WHERE quiz.id NOT IN (
        SELECT quiz_id FROM scores WHERE user_id = ?
    )
    AND (LOWER(quiz.quiz_name) LIKE ?)
    ORDER BY quiz.date ASC
    '''
    
    cursor.execute(query_all_quizzes, (session['user_id'], f'%{search_query}%'))
    all_quizzes = cursor.fetchall()

    # Separate quizzes:
    upcoming_quizzes = [{
        "id": quiz["id"], 
        "quiz_name": quiz["quiz_name"], 
        "date": quiz["date"], 
        "no_of_qns": quiz["no_of_qns"]
    } for quiz in all_quizzes if quiz["date"] > today_str][:3]  # Only top 3 future quizzes

    current_quizzes = [{
        "id": quiz["id"], 
        "quiz_name": quiz["quiz_name"], 
        "duration": quiz["duration"], 
        "no_of_qns": quiz["no_of_qns"]
    } for quiz in all_quizzes if quiz["date"] <= today_str]  # All quizzes today or earlier

    conn.close()
    return render_template('student.html', 
                           score=score, 
                           student_name=student_name, 
                           upcoming_quizzes=upcoming_quizzes,  # Only topic, date, questions
                           current_quizzes=current_quizzes,  # Only topic, questions, duration
                           search_query=search_query)


@app.route('/attempt_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required(role='student')
def attempt_quiz(quiz_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Optional: Verify the quiz exists
    cursor.execute("SELECT quiz_name, duration FROM quiz WHERE id = ?", (quiz_id,))
    quiz = cursor.fetchone()
    if not quiz:
        conn.close()
        flash("Quiz not found.", "error")
        return redirect(url_for('student_page'))

    if request.method == 'POST':
        selected_answers = request.form  # Get submitted answers

        # Retrieve all questions for this quiz
        cursor.execute("SELECT id, correct_option FROM question WHERE quiz_id = ?", (quiz_id,))
        questions = cursor.fetchall()

        score = 0
        for question in questions:
            question_id = f"q{question['id']}"  # Match form input names
            correct_answer = str(question['correct_option'])
            if question_id in selected_answers and selected_answers[question_id] == correct_answer:
                score += 1  # Increase score if correct

        # Always update the attempt with the new score
        cursor.execute("SELECT total_user_score FROM scores WHERE quiz_id = ? AND user_id = ?", 
                       (quiz_id, session['user_id']))
        existing_score = cursor.fetchone()

        if existing_score:
            # Update the record with the new score (and refresh the timestamp)
            cursor.execute(
                "UPDATE scores SET total_user_score = ?, timestamp = CURRENT_TIMESTAMP WHERE quiz_id = ? AND user_id = ?",
                (score, quiz_id, session['user_id'])
            )
        else:
            # Insert new score if no previous attempt exists
            cursor.execute(
                "INSERT INTO scores (quiz_id, user_id, total_user_score) VALUES (?, ?, ?)",
                (quiz_id, session['user_id'], score)
            )

        # Recalculate the user's cumulative score from the scores table
        cursor.execute("""
            SELECT IFNULL(SUM(total_user_score), 0) AS total_score 
            FROM scores 
            WHERE user_id = ?
        """, (session['user_id'],))
        cumulative_score = cursor.fetchone()['total_score']

        # Update the user's cumulative score in the users table
        cursor.execute("UPDATE users SET score = ? WHERE id = ?", 
                       (cumulative_score, session['user_id']))

        conn.commit()
        conn.close()

        flash(f"Quiz submitted successfully! Your score: {score}", "success")
        return redirect(url_for('student_page'))

    else:
        # For GET requests, fetch all questions for the quiz
        cursor.execute("SELECT * FROM question WHERE quiz_id = ?", (quiz_id,))
        questions = cursor.fetchall()
        conn.close()
        return render_template('attempt.html', quiz=quiz, questions=questions)


@app.route('/finished_quizzes')
@login_required(role='student')
def finished_quizzes():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch completed quizzes based on scores table
    query = '''
    SELECT quiz.id, quiz.quiz_name, subject.name AS subject_name, scores.total_user_score
    FROM scores
    JOIN quiz ON scores.quiz_id = quiz.id
    JOIN chapter ON quiz.chapter_id = chapter.id
    JOIN subject ON chapter.subject_id = subject.id
    WHERE scores.user_id = ?
    ORDER BY scores.total_user_score DESC
    '''
    cursor.execute(query, (session['user_id'],))
    completed_quizzes = cursor.fetchall()

    conn.close()
    return render_template('finished_quizzes.html', completed_quizzes=completed_quizzes)


@app.route('/view_right_answers/<int:quiz_id>')
@login_required(role='student')
def view_right_answers(quiz_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch questions and correct answers
    query = '''
    SELECT question.question_text, question.option_1, question.option_2, 
           question.option_3, question.option_4, question.correct_option
    FROM question
    WHERE question.quiz_id = ?
    '''
    cursor.execute(query, (quiz_id,))
    questions = cursor.fetchall()
    
    conn.close()
    return render_template('view_right_answers.html', questions=questions)


@app.route('/reattempt_quiz/<int:quiz_id>')
@login_required(role='student')
def reattempt_quiz(quiz_id):
    return redirect(url_for('attempt_quiz', quiz_id=quiz_id))


@app.route('/manage_quizzes', methods=['GET'])
@login_required(role='admin')
def manage_quizzes():
    search_query = request.args.get('search', '')  # Get the search query from the URL

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Use a filter if a search query exists
    if search_query:
        query = '''
        SELECT q.quiz_name, q.id, c.name, q.remark, q.no_of_qns
        FROM quiz q
        JOIN chapter c ON q.chapter_id = c.id
        WHERE c.name LIKE ? OR q.remark LIKE ?
        '''
        cursor.execute(query, (f'%{search_query}%', f'%{search_query}%'))
    else:
        # If no search query, return all quizzes
        query = '''
        SELECT q.quiz_name, q.id, c.name, q.remark, q.no_of_qns
        FROM quiz q
        JOIN chapter c ON q.chapter_id = c.id
        '''
        cursor.execute(query)

    quizzes = cursor.fetchall()  # Fetch the quizzes from the database
    print(quizzes)
    conn.close()

    return render_template('manage_quizzes.html', quizzes=quizzes)


@app.route('/leaderboard')
@login_required(role='admin')
def leaderboard():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Use Row objects for column access
    cursor = conn.cursor()

    # KPI 1: Total Students (count users)
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    total_students = cursor.fetchone()[0]

    # KPI 2: Overall Average Score (normalized)
    cursor.execute("""
        SELECT AVG(score_perc) FROM (
            SELECT s.total_user_score * 1.0 / q.no_of_qns AS score_perc
            FROM scores s
            JOIN quiz q ON s.quiz_id = q.id
        )
    """)
    overall_avg = cursor.fetchone()[0] or 0
    overall_avg = overall_avg * 100
    overall_avg = round(overall_avg, 1)

    # KPI 3: Highest Total Score (group by user in scores table)
    cursor.execute("""
        SELECT MAX(total_score) AS highest_total_score FROM (
            SELECT user_id, SUM(total_user_score) AS total_score
            FROM scores
            GROUP BY user_id
        )
    """)
    highest_total_score = cursor.fetchone()[0] or 0

    # KPI 4: Best Performing Subject (group by subject and sum scores)
    cursor.execute("""
        SELECT sub.name, SUM(s.total_user_score) AS total_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        JOIN subject sub ON ch.subject_id = sub.id
        GROUP BY sub.id
        ORDER BY total_score DESC
        LIMIT 1
    """)
    best_sub_row = cursor.fetchone()
    best_subject = best_sub_row[0] if best_sub_row else "N/A"

    # Subject-wise Cumulative Scores (as lists)
    cursor.execute("""
        SELECT sub.name, SUM(s.total_user_score) AS sum_score, SUM(q.no_of_qns) AS max_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        JOIN subject sub ON ch.subject_id = sub.id
        GROUP BY sub.id
        ORDER BY sub.name
    """)
    subject_cumulative = [list(row) for row in cursor.fetchall()]

    # Subject-wise Average Scores (as lists)
    cursor.execute("""
        SELECT sub.name, AVG(s.total_user_score * 1.0 / q.no_of_qns) AS avg_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        JOIN subject sub ON ch.subject_id = sub.id
        GROUP BY sub.id
        ORDER BY sub.name
    """)
    subject_average = [list(row) for row in cursor.fetchall()]

    # Subject-wise Attempts (as lists)
    cursor.execute("""
        SELECT sub.name, COUNT(*) AS attempts
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        JOIN subject sub ON ch.subject_id = sub.id
        GROUP BY sub.id
        ORDER BY sub.name
    """)
    subject_attempts = [list(row) for row in cursor.fetchall()]

    # User-wise Cumulative Scores (as lists)
    cursor.execute("""
        SELECT u.fullname, SUM(s.total_user_score) AS total_score, SUM(q.no_of_qns) AS total_possible
        FROM scores s
        JOIN users u ON s.user_id = u.id
        JOIN quiz q ON s.quiz_id = q.id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY total_score DESC
    """)
    user_cumulative = [list(row) for row in cursor.fetchall()]

    # All Students Performance (as lists)
    cursor.execute("""
        SELECT u.fullname, u.username,
               IFNULL(SUM(s.total_user_score), 0) AS total_score,
               IFNULL(SUM(q.no_of_qns), 0) AS total_possible
        FROM users u
        LEFT JOIN scores s ON u.id = s.user_id
        LEFT JOIN quiz q ON s.quiz_id = q.id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY u.fullname
    """)
    all_students = [list(row) for row in cursor.fetchall()]

    # Top 5 Quizzes by Average Score (as lists)
    cursor.execute("""
        SELECT q.quiz_name, AVG(s.total_user_score * 1.0 / q.no_of_qns) AS avg_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        GROUP BY q.id
        ORDER BY avg_score DESC
        LIMIT 5
    """)
    top_quizzes = [list(row) for row in cursor.fetchall()]

    # Lowest 5 Quizzes by Average Score (as lists)
    cursor.execute("""
        SELECT q.quiz_name, AVG(s.total_user_score * 1.0 / q.no_of_qns) AS avg_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        GROUP BY q.id
        ORDER BY avg_score ASC
        LIMIT 5
    """)
    lowest_quizzes = [list(row) for row in cursor.fetchall()]

    # Pass/Fail Ratio (single row, no conversion needed)
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN s.total_user_score * 1.0 / q.no_of_qns >= 0.5 THEN 1 ELSE 0 END) AS pass_count,
            SUM(CASE WHEN s.total_user_score * 1.0 / q.no_of_qns < 0.5 THEN 1 ELSE 0 END) AS fail_count
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
    """)
    pf_row = cursor.fetchone()
    pass_count = pf_row[0] if pf_row and pf_row[0] is not None else 0
    fail_count = pf_row[1] if pf_row and pf_row[1] is not None else 0

    conn.close()

    return render_template('leaderboard.html',
                           total_students=total_students,
                           overall_avg=overall_avg,
                           highest_total_score=highest_total_score,
                           best_subject=best_subject,
                           subject_cumulative=subject_cumulative,
                           subject_average=subject_average,
                           subject_attempts=subject_attempts,
                           user_cumulative=user_cumulative,
                           all_students=all_students,
                           top_quizzes=top_quizzes,
                           lowest_quizzes=lowest_quizzes,
                           pass_count=pass_count,
                           fail_count=fail_count)


def log_tables():
    import sqlite3
    conn = sqlite3.connect("quiz.db")
    conn.row_factory = sqlite3.Row  # to access columns by name
    cursor = conn.cursor()

    # Log the Users table
    print("Users Table:")
    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        print(dict(row))  # convert each row to a dictionary for clearer output

    # Log the Scores table
    print("\nScores Table:")
    cursor.execute("SELECT * FROM scores")
    for row in cursor.fetchall():
        print(dict(row))

    conn.close()


@app.route('/profile')
@login_required(role='student')
def profile():
    user_id = session.get("user_id")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch user profile details (excluding password)
    cursor.execute("""
        SELECT username, fullname, qualification, dob, role 
        FROM users 
        WHERE id = ?
    """, (user_id,))
    user_profile = cursor.fetchone()

    # Fetch maximum quiz score for the user (best single attempt)
    cursor.execute("SELECT MAX(total_user_score) FROM scores WHERE user_id = ?", (user_id,))
    max_score = cursor.fetchone()[0] or 0

    # Fetch cumulative and average quiz scores (average as percentage)
    cursor.execute("""
        SELECT SUM(s.total_user_score), AVG((s.total_user_score*100.0)/q.no_of_qns)
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        WHERE s.user_id = ?
    """, (user_id,))
    cum_avg = cursor.fetchone()
    cumulative_score = cum_avg[0] or 0
    average_score = round(cum_avg[1] or 0, 2)

    # Fetch top three chapters (by average quiz percentage per chapter)
    cursor.execute("""
        SELECT ch.name, AVG((s.total_user_score*100.0)/q.no_of_qns) AS avg_percentage
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        WHERE s.user_id = ?
        GROUP BY ch.id
        ORDER BY avg_percentage DESC
        LIMIT 3
    """, (user_id,))
    top_chapters = cursor.fetchall()

    # Fetch all quiz scores along with number of questions for distribution
    cursor.execute("""
        SELECT s.total_user_score, q.no_of_qns
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        WHERE s.user_id = ?
    """, (user_id,))
    all_scores = cursor.fetchall()

    # Fetch quizzes by subject (count of quizzes per subject)
    cursor.execute("""
        SELECT sub.name, COUNT(*) as quiz_count
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        JOIN subject sub ON ch.subject_id = sub.id
        WHERE s.user_id = ?
        GROUP BY sub.id
        ORDER BY quiz_count DESC
    """, (user_id,))
    quizzes_by_subject = cursor.fetchall()

    conn.close()

    return render_template('profile.html',
                           user_profile=user_profile,
                           max_score=max_score,
                           cumulative_score=cumulative_score,
                           average_score=average_score,
                           top_chapters=top_chapters,
                           all_scores=all_scores,
                           quizzes_by_subject=quizzes_by_subject)


@app.route('/admin/addsub', methods=['GET', 'POST'])
@login_required(role='admin')
def add_subject():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        description = request.form['description']
        
        # Validate input
        if not name or not description:
            flash("Both name and description are required!", "error")  # Use flash for error
            return redirect(url_for('add_subject'))  # Redirect back to the form page

        # Check if the subject already exists
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subject WHERE name = ?', (name,))
        existing_subject = cursor.fetchone()

        if existing_subject:
            flash("A subject with this name already exists!", "error")  # Flash error message
            conn.close()
            return redirect(url_for('add_subject'))  # Redirect back to the form page

        # Insert into the database
        cursor.execute('INSERT INTO subject (name, description) VALUES (?, ?)', (name, description))
        conn.commit()
        conn.close()


        # Redirect to the admin page after adding
        return redirect(url_for('admin'))  # Corrected to use the correct endpoint name
    return render_template('addsub.html')


@app.route('/admin/<int:subject_id>', methods=['GET'])
@login_required(role='admin')
def manage_chapters(subject_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get subject name
    cursor.execute('SELECT name FROM subject WHERE id = ?', (subject_id,))
    subject_name = cursor.fetchone()

    if not subject_name:
        conn.close()
        return "Subject not found", 404

    # Get chapters for this subject
    cursor.execute('''
        SELECT id, name, description
        FROM chapter
        WHERE subject_id = ?
    ''', (subject_id,))
    chapters = cursor.fetchall()
    conn.close()

    return render_template('manage_chapters.html', subject_id=subject_id, subject_name=subject_name[0], chapters=chapters)


@app.route('/admin/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_chapter(chapter_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        # Fetch the subject_id for redirection after editing
        cursor.execute('SELECT subject_id FROM chapter WHERE id = ?', (chapter_id,))
        subject_id = cursor.fetchone()
        if not subject_id:
            conn.close()
            return "Chapter not found", 404
        subject_id = subject_id[0]

        # Update the chapter
        cursor.execute(''' 
            UPDATE chapter
            SET name = ?, description = ?
            WHERE id = ?
        ''', (name, description, chapter_id))
        conn.commit()
        conn.close()

        # Redirect to manage_chapters with the correct subject_id
        return redirect(url_for('manage_chapters', subject_id=subject_id))

    # Fetch the current chapter data for pre-filling the form
    cursor.execute('SELECT name, description, subject_id FROM chapter WHERE id = ?', (chapter_id,))
    chapter = cursor.fetchone()
    conn.close()

    if not chapter:
        return "Chapter not found", 404

    # Use the old approach here to pass the values as a dictionary
    chapter_data = {
        'name': chapter[0],         # Pre-fill with current name
        'description': chapter[1],  # Pre-fill with current description
        'subject_id': chapter[2]    # Pre-fill with subject ID for redirection
    }

    # Render the add_chapter.html with the prefilled form
    return render_template('add_chapter.html', chapter=chapter_data, is_edit=True)


@app.route('/admin/<int:subject_id>/add_chapter', methods=['GET', 'POST'])
@login_required(role='admin')
def add_chapter(subject_id):
    # Check if we're editing an existing chapter
    chapter_id = request.args.get('chapter_id')  # Get chapter_id from URL parameters
    chapter = None
    
    if chapter_id:
        # Fetch chapter details if editing
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description FROM chapter WHERE id = ?', (chapter_id,))
        chapter = cursor.fetchone()
        conn.close()

        # If chapter doesn't exist, return error
        if not chapter:
            return "Chapter not found", 404

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            if chapter:  # If we are editing an existing chapter
                cursor.execute('''
                    UPDATE chapter
                    SET name = ?, description = ?
                    WHERE id = ?
                ''', (name, description, chapter_id))
            else:  # If we are adding a new chapter
                cursor.execute('''
                    INSERT INTO chapter (name, description, subject_id)
                    VALUES (?, ?, ?)
                ''', (name, description, subject_id))
            conn.commit()
        except Exception as e:
            conn.close()
            return render_template('add_chapter.html', error="Failed to save chapter. Try again.")
        
        conn.close()
        return redirect(url_for('manage_chapters', subject_id=subject_id))

    # Render the add_chapter page (pass chapter data for editing if available)
    return render_template('add_chapter.html', subject_id=subject_id, chapter=chapter, is_edit=bool(chapter))


@app.route('/admin/delete_chapter/<int:chapter_id>', methods=['POST'])
@login_required(role='admin')
def delete_chapter(chapter_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM chapter WHERE id = ?', (chapter_id,))
        conn.commit()
    except Exception as e:
        conn.close()
        return "Failed to delete chapter", 500

    conn.close()
    return redirect(request.referrer or url_for('admin'))


@app.route('/manage_quizzes/add_quiz', methods=['GET', 'POST'])
@login_required(role='admin')
def add_quiz():
    # Fetch selected subject ID from query parameters or form data
    selected_subject_id = request.args.get('subject_id') or request.form.get('subject_id')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch all subjects
    cursor.execute('SELECT id, name FROM subject')
    subjects = cursor.fetchall()

    # Fetch chapters for the selected subject
    if selected_subject_id:
        cursor.execute('SELECT id, name FROM chapter WHERE subject_id = ?', (selected_subject_id,))
    else:
        cursor.execute('SELECT id, name FROM chapter')
    chapters = cursor.fetchall()

    if request.method == 'POST':
        # Fetch form data
        subject_id = request.form.get('subject_id')
        chapter_id = request.form.get('chapter_id')
        q_name = request.form.get('q_name')
        description = request.form.get('description')
        quiz_date = request.form.get('quiz_date')  # New field for quiz date

        # Insert quiz into the database using the provided quiz date
        if subject_id and chapter_id and description and quiz_date:
            try:
                cursor.execute('''
                    INSERT INTO quiz (quiz_name, chapter_id, date, duration, remark, no_of_qns)
                    VALUES (?, ?, ?, 30, ?, 0)
                ''', (q_name, chapter_id, quiz_date, description))
                conn.commit()
                return redirect(url_for('manage_quizzes'))
            except Exception as e:
                flash(f"Failed to add quiz: {e}", "error")

    conn.close()

    return render_template(
        'add_quiz.html',
        subjects=subjects,
        chapters=chapters,
        selected_subject_id=selected_subject_id
    )


@app.route('/manage_quizzes/<int:quiz_id>', methods=['GET'])
@login_required(role='admin')
def manage_questions(quiz_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get quiz name
    cursor.execute('SELECT quiz_name FROM quiz WHERE id = ?', (quiz_id,))
    quiz_name = cursor.fetchone()

    if not quiz_name:
        conn.close()
        return "Quiz not found", 404

    # Get questions and their details for this quiz
    cursor.execute('''
        SELECT id, question_text, option_1, option_2, option_3, option_4, correct_option
        FROM question
        WHERE quiz_id = ?
    ''', (quiz_id,))
    questions = cursor.fetchall()
    conn.close()

    return render_template(
        'manage_questions.html',
        quiz_id=quiz_id,
        quiz_name=quiz_name[0],
        questions=questions
    )


app.route('/admin/leaderboard')
@login_required(role='admin')
def leaderboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Top 10 scorers overall (based on highest score per student)
    cursor.execute("""
        SELECT u.fullname, MAX(s.total_user_score) as highscore
        FROM scores s
        JOIN users u ON s.user_id = u.id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY highscore DESC
        LIMIT 10
    """)
    top_scorers = cursor.fetchall()  # List of tuples: (fullname, highscore)

    # Average score per quiz
    cursor.execute("""
        SELECT q.quiz_name, AVG(s.total_user_score) as avg_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        GROUP BY q.id
    """)
    quiz_avg_scores = cursor.fetchall()  # (quiz_name, avg_score)

    # Average score per subject
    cursor.execute("""
        SELECT sub.name as subject, AVG(s.total_user_score) as avg_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        JOIN subject sub ON ch.subject_id = sub.id
        GROUP BY sub.id
    """)
    subject_avg_scores = cursor.fetchall()  # (subject, avg_score)

    # Average score per chapter
    cursor.execute("""
        SELECT ch.name as chapter, AVG(s.total_user_score) as avg_score
        FROM scores s
        JOIN quiz q ON s.quiz_id = q.id
        JOIN chapter ch ON q.chapter_id = ch.id
        GROUP BY ch.id
    """)
    chapter_avg_scores = cursor.fetchall()  # (chapter, avg_score)

    conn.close()

    # Pass JSON strings for Chart.js consumption
    return render_template(
        'leaderboard.html',
        top_scorers=top_scorers,
        quiz_avg_scores=quiz_avg_scores,
        subject_avg_scores=subject_avg_scores,
        chapter_avg_scores=chapter_avg_scores,
        top_scorers_json=json.dumps(top_scorers),
        quiz_avg_scores_json=json.dumps(quiz_avg_scores),
        subject_avg_scores_json=json.dumps(subject_avg_scores),
        chapter_avg_scores_json=json.dumps(chapter_avg_scores)
    )


@app.route('/manage_quizzes/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_question(question_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        question_text = request.form['question_text']
        option_1 = request.form['option_1']
        option_2 = request.form['option_2']
        option_3 = request.form['option_3']
        option_4 = request.form['option_4']
        correct_option = request.form['correct_option']

        # Fetch the quiz_id for redirection after editing
        cursor.execute('SELECT quiz_id FROM question WHERE id = ?', (question_id,))
        quiz_id = cursor.fetchone()
        if not quiz_id:
            conn.close()
            return "Question not found", 404
        quiz_id = quiz_id[0]

        # Update the question
        cursor.execute(''' 
            UPDATE question
            SET question_text = ?, option_1 = ?, option_2 = ?, option_3 = ?, option_4 = ?, correct_option = ?
            WHERE id = ?
        ''', (question_text, option_1, option_2, option_3, option_4, correct_option, question_id))
        conn.commit()
        conn.close()

        # Redirect to manage_quizzes with the correct quiz_id
        return redirect(url_for('manage_questions', quiz_id=quiz_id))

    # Fetch the current question data for pre-filling the form
    cursor.execute('SELECT question_text, option_1, option_2, option_3, option_4, correct_option, quiz_id FROM question WHERE id = ?', (question_id,))
    question = cursor.fetchone()
    conn.close()

    if not question:
        return "Question not found", 404

    # Pass the question data to pre-fill the form
    question_data = {
        'question_text': question[0],         # Pre-fill with current question text
        'option_1': question[1],              # Pre-fill with current option 1
        'option_2': question[2],              # Pre-fill with current option 2
        'option_3': question[3],              # Pre-fill with current option 3
        'option_4': question[4],              # Pre-fill with current option 4
        'correct_option': question[5],        # Pre-fill with current correct option
        'quiz_id': question[6]                # Pre-fill with quiz ID for redirection
    }

    # Render the add_question.html with the prefilled form
    return render_template('add_question.html', question=question_data, is_edit=True)


@app.route('/manage_quizzes/add_question/<int:quiz_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def add_question(quiz_id):
    if request.method == 'POST':
        question_text = request.form['question_text']
        option_1 = request.form['option_1']
        option_2 = request.form['option_2']
        option_3 = request.form['option_3']
        option_4 = request.form['option_4']
        correct_option = request.form['correct_option']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(''' 
                INSERT INTO question (question_text, option_1, option_2, option_3, option_4, correct_option, quiz_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_text, option_1, option_2, option_3, option_4, correct_option, quiz_id))
            cursor.execute('''UPDATE quiz SET no_of_qns = no_of_qns + 1 WHERE id = ?''', (quiz_id,))
            conn.commit()
        except Exception as e:
            conn.close()
            return render_template('add_question.html', error="Failed to save question. Try again.")
        
        conn.close()
        return redirect(url_for('manage_questions', quiz_id=quiz_id))

    # Render the add_question page
    return render_template('add_question.html', quiz_id=quiz_id, is_edit=False)


@app.route('/manage_quizzes/delete_question/<int:question_id>', methods=['POST'])
@login_required(role='admin')
def delete_question(question_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Fetch the quiz_id for redirection after deletion
        cursor.execute('SELECT quiz_id FROM question WHERE id = ?', (question_id,))
        quiz_id = cursor.fetchone()
        if not quiz_id:
            conn.close()
            return "Question not found", 404
        quiz_id = quiz_id[0]

        cursor.execute('DELETE FROM question WHERE id = ?', (question_id,))
        cursor.execute('''UPDATE quiz SET no_of_qns = no_of_qns - 1 WHERE id = ?''', (quiz_id,))
        conn.commit()
        conn.close()

        # Redirect to manage_quizzes with the correct quiz_id
        return redirect(url_for('manage_questions', quiz_id=quiz_id))
    except Exception as e:
        conn.close()
        return "Error deleting question", 500


@app.route('/manage_quizzes/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_quiz(quiz_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        quiz_name = request.form['quiz_name']
        remark = request.form['remark']

        cursor.execute('''
            UPDATE quiz
            SET quiz_name = ?, remark = ?
            WHERE id = ?
        ''', (quiz_name, remark, quiz_id))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_questions', quiz_id=quiz_id))

    cursor.execute('SELECT quiz_name, remark FROM quiz WHERE id = ?', (quiz_id,))
    quiz = cursor.fetchone()
    conn.close()

    if not quiz:
        return "Quiz not found", 404

    return render_template('edit_quiz.html', quiz=quiz, quiz_id=quiz_id)


@app.route('/manage_quizzes/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required(role='admin')
def delete_quiz(quiz_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Delete all questions associated with the quiz
    cursor.execute('''
        DELETE FROM question WHERE quiz_id = ?
    ''', (quiz_id,))

    # Delete the quiz itself
    cursor.execute('''
        DELETE FROM quiz WHERE id = ?
    ''', (quiz_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('manage_quizzes'))


@app.route('/admin/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_subject(subject_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        subject_name = request.form['subject_name']
        description = request.form['description']

        cursor.execute(''' 
            UPDATE subject
            SET name = ?, description = ?
            WHERE id = ?
        ''', (subject_name, description, subject_id))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_chapters', subject_id=subject_id))

    cursor.execute('SELECT name, description FROM subject WHERE id = ?', (subject_id,))
    subject = cursor.fetchone()
    conn.close()

    if not subject:
        return "Subject not found", 404

    return render_template('edit_sub.html', subject=subject, subject_id=subject_id)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)  # Remove role from session
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
