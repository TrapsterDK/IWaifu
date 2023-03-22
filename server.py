from flask import Flask, render_template, request, redirect, url_for
from sqlite import get_db, close_db
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

URL_INDEX = '/'
URL_LOGIN = '/login'
URL_LOGOUT = '/logout'
URL_SIGNUP = '/signup'

JINJA_INDEX = 'index.jinja'
JINJA_LOGIN = 'login.jinja'
JINJA_SIGNUP = 'signup.jinja'


app = Flask(__name__)
app.config['DEBUG'] = True
app.config['DATABASE'] = 'database.db'


login_manager = LoginManager()
login_manager.init_app(app)


@app.teardown_appcontext
def teardown(execption):
    close_db()


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.get_user(user_id)
    return user


@app.route(URL_INDEX, methods=['GET'])
def index():
    return render_template(JINJA_INDEX)


@app.route(URL_SIGNUP, methods=['GET'])
def signup_get():
    return render_template(JINJA_SIGNUP)

@app.route(URL_SIGNUP, methods=['POST'])
def signup_post():
    if current_user.is_authenticated:
        return redirect(url_for(URL_INDEX))
    
    if all(x in request.form for x in ['username','password', 'email']):
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        db = get_db()
        if not db.add_user(username, password, email):
            return 'Username or email already exists'

        return 1

    return 'Missing username, password, or email'


@app.route(URL_LOGIN, methods=['GET'])
def login_get():
    return render_template(JINJA_LOGIN)

@app.route(URL_LOGIN, methods=['POST'])
def login_post():
    if 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form and request.form['remember'] == True
        
        db = get_db()
        user_id = db.get_username_id(username)
        if user_id == None:
            return 'Incorrect username or password'
        
        user = db.get_user(user_id)
        if not db.verify_user(password, user['salt'], user['password']):
            return 'Incorrect username or password'

        login_user(user, remember=remember)

        return 1
    
    return 'Missing email or password'


@app.route(URL_LOGOUT, methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for(URL_INDEX))


if __name__ == '__main__':
    print('Starting server...')
    app.run(debug=True)