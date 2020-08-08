# __init__.py
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    app.config['DATABASE'] = 'quiz.db'
    app.config['SECRET_ADMIN_NAME'] = '_secadmin'
    # TODO Check if the following is used for anything - think probably not.
    app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
    # TODO Seen a suggestion that I should be using instance_path instead of root_path -
    #  not sure why or what the instance folder is for.  Need to do some research.
    db_file = os.path.join(app.root_path, 'quiz.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Upload size limit

    app.secret_key = os.urandom(16)

    db.init_app(app)

    # blueprint for non-auth parts of app
    # from .quiz import quiz as main_blueprint
    # app.register_blueprint(main_blueprint)

    from . import quiz
    app.register_blueprint(quiz.quiz)
    app.add_url_rule('/', endpoint='main')

    return app
