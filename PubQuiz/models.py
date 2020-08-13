# models.py
from sqlalchemy import select, func, and_
from sqlalchemy.orm import column_property

from . import db


class Questions(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('rounds.id'), nullable=False)
    round = db.relationship("Round", back_populates="questions")

    r_num = db.Column(db.Integer, nullable=False)
    q_num = db.Column(db.Integer, nullable=False)
    question = db.Column(db.Text, nullable=False)
    type = db.Column(db.Text, nullable=False)
    choices = db.Column(db.Text)
    answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)

    responses = db.relationship("Response", back_populates="question")


class Round(db.Model):
    __tablename__ = 'rounds'
    id = db.Column(db.Integer, primary_key=True)
    questions = db.relationship("Questions", back_populates="round", order_by=Questions.q_num)
    r_num = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)


class Response(db.Model):
    __tablename__ = 'responses'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)

    r_num = db.Column(db.Integer)
    q_num = db.Column(db.Integer)
    name = db.Column(db.Text)
    answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer)
    hidden = db.Column(db.Integer, nullable=False)
    question = db.relationship("Questions", back_populates="responses")
    player = db.relationship("Player", back_populates="responses")


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)  # primary keys are required by SQLAlchemy
    responses = db.relationship("Response", back_populates="player")

    name = db.Column(db.Text, unique=True, nullable=False)
    last_seen = db.Column(db.Integer)

    score = column_property(
        select([func.sum(Response.score)]).where(and_(Response.player_id == id, Response.hidden == 0)).correlate_except(
            Response)
    )


class State(db.Model):
    __tablename__ = 'state'
    id = db.Column(db.Integer, primary_key=True)

    r_num = db.Column(db.Integer, nullable=False)
    q_num = db.Column(db.Integer, nullable=False)
    done = db.Column(db.Integer, nullable=False)
