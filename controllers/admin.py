from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import sqlite3
import datetime
import random
import os
from functools import wraps
from functools import wraps

DATABASE = "quiz.db"

admin_bp = Blueprint('admin', __name__)

# Login required decorator with role check
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('admin.login'))  # Redirect to login if not logged in

            # Check if user has the correct role
            if role and session.get('role') != role:
                return redirect(url_for('admin.login'))  # Redirect if user doesn't have the correct role

            return f(*args, **kwargs)

        return decorated_function
    return decorator

@admin_bp.route('/admin', methods=['GET'])
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


@admin_bp.route('/manage_quizzes', methods=['GET'])
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


@admin_bp.route('/leaderboard')
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


@admin_bp.route('/admin/addsub', methods=['GET', 'POST'])
@login_required(role='admin')
def add_subject():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        description = request.form['description']
        
        # Validate input
        if not name or not description:
            flash("Both name and description are required!", "error")  # Use flash for error
            return redirect(url_for('admin.add_subject'))  # Redirect back to the form page

        # Check if the subject already exists
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subject WHERE name = ?', (name,))
        existing_subject = cursor.fetchone()

        if existing_subject:
            flash("A subject with this name already exists!", "error")  # Flash error message
            conn.close()
            return redirect(url_for('admin.add_subject'))  # Redirect back to the form page

        # Insert into the database
        cursor.execute('INSERT INTO subject (name, description) VALUES (?, ?)', (name, description))
        conn.commit()
        conn.close()


        # Redirect to the admin page after adding
        return redirect(url_for('admin.admin'))  # Corrected to use the correct endpoint name
    return render_template('addsub.html')


@admin_bp.route('/admin/<int:subject_id>', methods=['GET'])
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


@admin_bp.route('/admin/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.manage_chapters', subject_id=subject_id))

    # Fetch the current chapter data for pre-filling the form
    cursor.execute('SELECT name, description, subject_id FROM chapter WHERE id = ?', (chapter_id,))
    chapter = cursor.fetchone()
    conn.close()

    if not chapter:
        return "Chapter not found", 404

    # Use the old admin_bproach here to pass the values as a dictionary
    chapter_data = {
        'name': chapter[0],         # Pre-fill with current name
        'description': chapter[1],  # Pre-fill with current description
        'subject_id': chapter[2]    # Pre-fill with subject ID for redirection
    }

    # Render the add_chapter.html with the prefilled form
    return render_template('add_chapter.html', chapter=chapter_data, is_edit=True)


@admin_bp.route('/admin/<int:subject_id>/add_chapter', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.manage_chapters', subject_id=subject_id))

    # Render the add_chapter page (pass chapter data for editing if available)
    return render_template('add_chapter.html', subject_id=subject_id, chapter=chapter, is_edit=bool(chapter))


@admin_bp.route('/admin/delete_chapter/<int:chapter_id>', methods=['POST'])
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
    return redirect(request.referrer or url_for('admin.admin'))


@admin_bp.route('/manage_quizzes/add_quiz', methods=['GET', 'POST'])
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
                return redirect(url_for('admin.manage_quizzes'))
            except Exception as e:
                flash(f"Failed to add quiz: {e}", "error")

    conn.close()

    return render_template(
        'add_quiz.html',
        subjects=subjects,
        chapters=chapters,
        selected_subject_id=selected_subject_id
    )


@admin_bp.route('/manage_quizzes/<int:quiz_id>', methods=['GET'])
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


admin_bp.route('/admin/leaderboard')
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


@admin_bp.route('/manage_quizzes/edit_question/<int:question_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))

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


@admin_bp.route('/manage_quizzes/add_question/<int:quiz_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))

    # Render the add_question page
    return render_template('add_question.html', quiz_id=quiz_id, is_edit=False)


@admin_bp.route('/manage_quizzes/delete_question/<int:question_id>', methods=['POST'])
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
        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))
    except Exception as e:
        conn.close()
        return "Error deleting question", 500


@admin_bp.route('/manage_quizzes/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
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

        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))

    cursor.execute('SELECT quiz_name, remark FROM quiz WHERE id = ?', (quiz_id,))
    quiz = cursor.fetchone()
    conn.close()

    if not quiz:
        return "Quiz not found", 404

    return render_template('edit_quiz.html', quiz=quiz, quiz_id=quiz_id)


@admin_bp.route('/manage_quizzes/delete_quiz/<int:quiz_id>', methods=['POST'])
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

    return redirect(url_for('admin.manage_quizzes'))


@admin_bp.route('/admin/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
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

        return redirect(url_for('admin.manage_chapters', subject_id=subject_id))

    cursor.execute('SELECT name, description FROM subject WHERE id = ?', (subject_id,))
    subject = cursor.fetchone()
    conn.close()

    if not subject:
        return "Subject not found", 404

    return render_template('edit_sub.html', subject=subject, subject_id=subject_id)
