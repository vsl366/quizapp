from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import datetime
from functools import wraps


DATABASE = "quiz.db"

student_bp = Blueprint('student', __name__)


# Login required decorator with role check
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('student.login'))  # Redirect to login if not logged in

            # Check if user has the correct role
            if role and session.get('role') != role:
                return redirect(url_for('student.login'))  # Redirect if user doesn't have the correct role

            return f(*args, **kwargs)

        return decorated_function
    return decorator



@student_bp.route('/student')
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


@student_bp.route('/attempt_quiz/<int:quiz_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('student.student_page'))

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
        return redirect(url_for('student.student_page'))

    else:
        # For GET requests, fetch all questions for the quiz
        cursor.execute("SELECT * FROM question WHERE quiz_id = ?", (quiz_id,))
        questions = cursor.fetchall()
        conn.close()
        return render_template('attempt.html', quiz=quiz, questions=questions)


@student_bp.route('/finished_quizzes')
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


@student_bp.route('/view_right_answers/<int:quiz_id>')
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


@student_bp.route('/reattempt_quiz/<int:quiz_id>')
@login_required(role='student')
def reattempt_quiz(quiz_id):
    return redirect(url_for('student.attempt_quiz', quiz_id=quiz_id))


@student_bp.route('/profile')
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


