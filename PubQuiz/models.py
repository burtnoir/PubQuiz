# models.py
from sqlalchemy import Sequence, ForeignKey, select, func, and_
from sqlalchemy.orm import relationship, column_property

from . import db


class Questions(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)
    responses = relationship("Response", back_populates="question")

    r_num = db.Column(db.Integer)
    q_num = db.Column(db.Integer)
    question = db.Column(db.Text)
    type = db.Column(db.Text)
    choices = db.Column(db.Text)
    answer = db.Column(db.Text)
    score = db.Column(db.Integer)


class Response(db.Model):
    __tablename__ = 'responses'
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)
    question_id = db.Column(db.Integer, ForeignKey('questions.id'))
    player_id = db.Column(db.Integer, ForeignKey('players.id'))

    r_num = db.Column(db.Integer)
    q_num = db.Column(db.Integer)
    name = db.Column(db.Text)
    answer = db.Column(db.Text)
    score = db.Column(db.Integer)
    hidden = db.Column(db.Integer)
    question = relationship("Questions", back_populates="responses")
    player = relationship("Player", back_populates="responses")


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)  # primary keys are required by SQLAlchemy
    responses = relationship("Response", back_populates="player")

    name = db.Column(db.Text, unique=True)
    last_seen = db.Column(db.Integer)

    score = column_property(
        select([func.sum(Response.score)]).where(and_(Response.player_id == id, Response.hidden == 0)).correlate_except(Response)
    )


class State(db.Model):
    __tablename__ = 'state'
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)

    r_num = db.Column(db.Integer)
    q_num = db.Column(db.Integer)
    done = db.Column(db.Integer)
