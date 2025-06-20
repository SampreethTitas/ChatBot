import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import openai
import csv
from sqlalchemy import Text
from io import StringIO
import os
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Create OpenAI client using latest SDK

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.0-flash')


# Load config from environment variables
#from dotenv import load_dotenv
#load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///chat.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# OpenAI key
#openai.api_key = os.getenv("OPENAI_API_KEY")


# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(Text, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_message = db.Column(db.Text)
    bot_response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='chats')


# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
@login_required
def index():
    history = ChatLog.query.filter_by(user_id=current_user.id).order_by(ChatLog.timestamp).all()
    return render_template('index.html', history=history)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for('register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid credentials.")
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
def admin():
    if current_user.username != "admin":
        flash("Unauthorized")
        return redirect(url_for('index'))
    all_chats = ChatLog.query.order_by(ChatLog.timestamp).all()
    return render_template('admin.html', chats=all_chats)

@app.route('/test-gemini')
def test_gemini():
    try:
        chat = gemini_model.start_chat()
        response = chat.send_message("Hello from Gemini!")
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/export')
@login_required
def export():
    if current_user.username != "admin":
        flash("Unauthorized")
        return redirect(url_for('index'))

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Username', 'User Message', 'Bot Response', 'Timestamp'])

    chats = ChatLog.query.join(User).add_columns(
        User.username, ChatLog.user_message, ChatLog.bot_response, ChatLog.timestamp
    ).all()

    for chat in chats:
        cw.writerow([chat.username, chat.user_message, chat.bot_response, chat.timestamp])

    output = StringIO()
    output.write(si.getvalue())
    output.seek(0)

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='chatlogs.csv'
    )


# SocketIO chat event
@socketio.on('user_message')
def handle_user_message(data):
    prompt = data['message']
    user_id = session.get('user_id')

    try:
        # Start chat and get response
        chat_session = gemini_model.start_chat(history=[])
        response = chat_session.send_message(prompt)
        reply = response.text.strip()

        # Save chat
        chat = ChatLog(user_id=user_id, user_message=prompt, bot_response=reply)
        db.session.add(chat)
        db.session.commit()

        # Send to client
        emit('bot_response', {'message': reply})

    except Exception as e:
        print("Gemini API error:", str(e))
        emit('bot_response', {'message': "Sorry, an error occurred."})

# Run the app
if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()
        db.create_all()
    socketio.run(app, debug=True)#host='0.0.0.0', port=5000)
