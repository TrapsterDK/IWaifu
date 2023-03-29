from flask import Flask, render_template, request, redirect
from sqlite import get_db, close_db
from flask_login import (
    LoginManager,
    current_user,
    login_user,
    logout_user,
    login_required,
    UserMixin,
)
import os

URL_INDEX = "/"
URL_LOGIN = "/login"
URL_LOGOUT = "/logout"
URL_SIGNUP = "/signup"

JINJA_INDEX = "waifu.jinja"
JINJA_LOGIN = "login.jinja"
JINJA_SIGNUP = "signup.jinja"

SUCCESS = "success"

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["DATABASE"] = "database.db"
app.secret_key = os.urandom(24)


@app.teardown_appcontext
def teardown(execption):
    close_db()


login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id: int, username: str, email: str):
        self.id = user_id
        self.username = username
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.get_user(user_id)
    if user is None:
        return None

    return User(user_id=user["id"], username=user["username"], email=user["email"])


@app.route(URL_INDEX, methods=["GET"])
def index():
    return render_template(JINJA_INDEX)


@app.route(URL_SIGNUP, methods=["GET"])
def signup_get():
    if current_user.is_authenticated:
        return redirect(URL_INDEX)

    return render_template(JINJA_SIGNUP)


@app.route(URL_SIGNUP, methods=["POST"])
def signup_post():
    if not all(x in request.form for x in ["username", "password", "email"]):
        return "Missing username, password, or email"

    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]

    if not (4 <= len(username) <= 20):
        return "Username does not meet requirements"

    if (
        not (6 <= len(password) <= 20)
        or not any(x.isupper() for x in password)
        or not any(x.islower() for x in password)
        or not any(x.isdigit() for x in password)
    ):
        return "Password does not meet requirements"

    db = get_db()
    new_user_id = db.add_user(username, password, email)
    if new_user_id == None:
        return "Username or email already exists"

    login_user(User(user_id=new_user_id, username=username, email=email), remember=True)

    return SUCCESS


@app.route(URL_LOGIN, methods=["GET"])
def login_get():
    if current_user.is_authenticated:
        return redirect(URL_INDEX)

    return render_template(JINJA_LOGIN)


@app.route(URL_LOGIN, methods=["POST"])
def login_post():
    if not all(x in request.form for x in ["email", "password"]):
        return "Missing email or password"

    email = request.form["email"]
    password = request.form["password"]
    remember = "remember" in request.form and request.form["remember"] == True

    db = get_db()
    user = db.get_username_user(email)
    if user == None:
        return "Incorrect email or password"

    if not db.verify_user(email, password):
        return "Incorrect email or password"

    login_user(
        User(user_id=user["id"], username=user["username"], email=email),
        remember=remember,
    )

    return SUCCESS


@app.route(URL_LOGOUT, methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(URL_INDEX)


if __name__ == "__main__":
    print("Starting server...")
    app.run(debug=True)
