from flask import Flask, render_template, request, redirect
from sqlite import Database
from flask_login import (
    LoginManager,
    current_user,
    login_user,
    logout_user,
    login_required,
    UserMixin,
)
import os
import openai
import pathlib
from dataclasses import dataclass
import re
import pyttsx3
from sqlite import Database
from datetime import datetime
import spacy
import random

# pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_lg-0.5.1.tar.gz
# nlp = spacy.load("en_core_sci_lg")

# https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz
nlp = spacy.load("en_core_sci_sm")


# Fake nlp
class FakeDoc:
    def __init__(self, text):
        self.text = text
        self.ents = []

    def __call__(self, text):
        return FakeDoc(text)

    def __iter__(self):
        return iter(self.ents)

    def __len__(self):
        return len(self.ents)


class FakeNLP:
    def __init__(self):
        pass

    def __call__(self, text):
        return FakeDoc(text)


# nlp = FakeNLP()

engine = pyttsx3.init()
voice = engine.getProperty("voices")
engine.setProperty("voice", voice[1].id)

openai.api_key = "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"

MODEL_WAIFU_PATH = pathlib.Path(__file__).parent / "static/models/"
AUDIOS_PATH = pathlib.Path(__file__).parent / "static/assets/audios/"

RE_SPLIT_CHAR_INT = re.compile(r"(\d+)")
waifus_dir = [dir for dir in pathlib.Path(MODEL_WAIFU_PATH).iterdir()]
waifus_names = [
    " ".join(
        re.split(RE_SPLIT_CHAR_INT, str(dir.stem).replace("_", " ").replace("-", " "))
    ).capitalize()
    for dir in waifus_dir
]

waifus_models = [
    str(next(dir.glob("**/model.json")).relative_to(pathlib.Path(__file__).parent))
    for dir in waifus_dir
]


@dataclass
class Model:
    name: str
    url: str


waifu_models = [Model(name, path) for name, path in zip(waifus_names, waifus_models)]


URL_INDEX = "/"
URL_LOGIN = "/login"
URL_LOGOUT = "/logout"
URL_SIGNUP = "/signup"
URL_CHAT = "/chat"

JINJA_INDEX = "waifu.jinja"
JINJA_LOGIN = "login.jinja"
JINJA_SIGNUP = "signup.jinja"

SUCCESS = "success"

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["DATABASE"] = "database.db"
app.secret_key = os.urandom(24)

db = Database(app.config["DATABASE"])


login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id: int, username: str, email: str):
        self.id = user_id
        self.username = username
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    # TODO
    return User(user_id=1, username="test", email="m@gmail.com")

    user = db.get_user(user_id)
    if user is None:
        return None

    return User(user_id=user["id"], username=user["username"], email=user["email"])


@app.route(URL_INDEX, methods=["GET"])
@login_required
def index():
    return render_template(JINJA_INDEX, models=waifu_models)


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

    new_user_id = db.add_user(username, password, email)
    if new_user_id == None:
        return "Username or email already exists"

    login_user(User(user_id=new_user_id, username=username, email=email), remember=True)

    return SUCCESS


@app.route(URL_LOGIN, methods=["GET"])
def login_get():
    login_user(User(user_id=1, username="test", email="m@gmail.com"), remember=True)

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

    user = db.get_user_from_email(email)
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


def generate_memory(user_id: int, waifu: str) -> str:
    messages = db.get_messages(user_id, waifu, 50)

    human_memory = []
    waifu_memory = []
    for message in messages:
        text = message["message"]
        doc = nlp(text)

        if message["from_user"] == True:
            human_memory.extend(doc.ents)
        else:
            waifu_memory.extend(doc.ents)

    return (human_memory, waifu_memory)


@app.route(URL_CHAT, methods=["POST"])
@login_required
def chat():
    # get message from request
    if "message" not in request.form:
        return "Missing message"

    if "waifu" not in request.form:
        return "Missing waifu"

    message = request.form["message"].strip()

    if message == "":
        return "Empty message"

    waifu = request.form["waifu"]

    if waifu not in waifus_names:
        return "Invalid waifu"

    db.add_message(current_user.id, waifu, message, True, datetime.now())

    human_memory, waifu_memory = generate_memory(current_user.id, waifu)
    print(human_memory, waifu_memory)

    completion = openai.Completion.create(
        engine="text-davinci-003",  # "text-davinci-003", "text-ada-001"
        prompt=f"""
You are a cute waifu, you full of emotions and love. Your name is {waifu}.
Be somewhat breif like a human dialogue, and display emotions.  

Human chat memory:
{','.join([str(x) for x in human_memory])}

Waifu chat memory:
{','.join([str(x) for x in waifu_memory])}

Human: 
{message}

Waifu:
""",
        temperature=0.7,
        top_p=1,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        max_tokens=500,
    )

    text = completion.choices[0].text

    waifu_time = datetime.now()
    db.add_message(current_user.id, waifu, text, False, waifu_time.timestamp())

    # TODO deletion
    AUDIOS_PATH.joinpath("user").mkdir(parents=True, exist_ok=True)
    file = AUDIOS_PATH.joinpath("user", str(hex(abs(hash(text))))[2:] + ".mp3")
    engine.save_to_file(text, str(file))
    engine.runAndWait()

    return {
        "message": completion.choices[0].text,
        "time": waifu_time.strftime("%H:%M"),
        "audio": str(file.relative_to(pathlib.Path(__file__).parent)),
    }


if __name__ == "__main__":
    print("Starting server...")
    app.run("localhost", debug=True)
    # app.run("0.0.0.0", debug=True)
