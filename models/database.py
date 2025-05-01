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

        
        conn.commit()
        conn.close()
# 
