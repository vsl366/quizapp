
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from models.database import init_db
from controllers.auth import auth_bp
from controllers.admin import admin_bp
from controllers.student import student_bp

app = Flask(__name__)
app.secret_key = "secret_key"

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)

if __name__ == '__main__':
    init_db()  
    app.run(debug=True)
