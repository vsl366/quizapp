import sqlite3
import os
import random
import datetime
DATABASE = "quiz.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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
# 