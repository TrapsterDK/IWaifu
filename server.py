from flask import Flask, render_template, request, redirect, url_for
from sqlite import get_db, close_db


app = Flask(__name__)
app.config['DEBUG'] = True
app.config['DATABASE'] = 'database.db'


@app.teardown_appcontext
def teardown(execption):
    close_db()


@app.route('/')
def index():
    return "here"


@app.route('/login' , methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
            username = request.form['username']
            password = request.form['password']
            
            db = get_db()

            if db.verify_user(username, password):
                return redirect(url_for('/'))
            
            error = 'Invalid username or password'

    return render_template('login.html', error=error)
    


if __name__ == '__main__':
    app.run()