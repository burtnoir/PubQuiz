import time
from functools import wraps

from flask import Blueprint, render_template, request, session, abort, redirect, current_app, url_for
from sqlalchemy import and_

from PubQuiz.models import Player, Questions, Response, State
from . import db

quiz = Blueprint('quiz', __name__)


# TODO Again should probably be handled by SQLAlchemy
# @quiz.teardown_appcontext
# def close_connection(exception):
#     db = getattr(g, '_database', None)
#     if db is not None:
#         db.close()


def admin_only(f):
    """
    Admin-only access decorator
    :param f:
    :return:
    """

    @wraps(f)
    def wrap(*args, **kwargs):
        # user is available from @login_required
        if not session.get('name') == current_app.config['SECRET_ADMIN_NAME']:
            return redirect(url_for('quiz.main'))
        return f(*args, **kwargs)

    return wrap


@quiz.route('/quiz_view')
def quiz_view():
    now_time = int(time.time())

    name = session.get('name', '')
    player = Player.query.filter(Player.name == name).one_or_none()
    if player is None:
        return 'NOLOGIN'
    else:
        player.last_seen = now_time
        db.session.commit()

    state = State.query.one()
    players = Player.query.filter(Player.name != current_app.config['SECRET_ADMIN_NAME']).order_by(
        Player.score.desc()).all()
    r_num: int = state.r_num
    q_num: int = state.q_num

    if r_num == 0:  # Quiz not started
        return render_template('quiz_not_started.html', players=players, name=name, now_time=now_time)

    questions = Questions.query.filter(and_(Questions.r_num == r_num, Questions.q_num <= q_num)).order_by(
        Questions.q_num).all()
    for question in questions:
        question.first_answer = question.answer.split(',')[0]
    responses = Response.query.filter(and_(Response.r_num == r_num, Response.player_id == player.id)).all()

    if state.done == 0:  # Active round
        answers = {}
        for r in responses:
            answers[r.q_num] = r.answer
        return render_template('quiz_round.html', players=players, name=name, now_time=now_time, r_num=r_num,
                               questions=questions, answers=answers, enumerate=enumerate)
    else:  # Completed round
        return render_template('quiz_round_done.html', players=players, name=name, now_time=now_time, r_num=r_num,
                               questions=questions, state=state)


@quiz.route('/quiz_endpoint', methods=['POST'])
def quiz_endpoint():
    name = session.get('name', '')

    if name == '':
        return abort(403)
    if name == current_app.config['SECRET_ADMIN_NAME']:
        return 'ok'

    player = Player.query.filter(Player.name == name).one()

    r_num = State.query.filter().one().r_num
    for param in request.form:
        if param.startswith('ans_'):
            q_num = int(param[4:])
            ans_val = request.form[param]
            response = Response.query.filter(
                and_(Response.r_num == r_num, Response.q_num == q_num, Response.player_id == player.id)).one_or_none()

            # Only update response if it is new
            if response is None or response.answer != ans_val:
                # Auto-score new answer
                score = 0
                question = Questions.query.filter(and_(Questions.r_num == r_num, Questions.q_num == q_num)).one()
                for right_answer in question.answer.split(','):
                    if ans_val.lower() == right_answer.lower():
                        score = question.score
                        break

                # Commit response
                if response is None:
                    response = Response(r_num=r_num, question_id=question.id, q_num=q_num, player_id=player.id,
                                        name=player.name, answer=ans_val, score=score, hidden=1)
                    db.session.add(response)
                else:
                    response.answer = ans_val
                    response.score = score
                db.session.commit()
    return 'ok'


@quiz.route('/control', methods=['GET', 'POST'])
@admin_only
def control():
    """
    Used by the quiz master to administer the quiz.
    It can be used to reset things or to move the questions backwards and forwards.
    :return:
    """
    state = State.query.filter().one()

    round_number = state.r_num
    question_number = state.q_num
    done = state.done
    # Done=1: About to reveal answer (suspense); Done=2: Answer revealed

    if request.method == 'POST':
        if request.form.get('next') is not None:
            # Move quiz forward
            next_question = Questions.query.filter(
                and_(Questions.r_num == round_number, Questions.q_num == question_number + 1)).one_or_none()
            if done == 1 and question_number > 0:
                # Reveal answer
                done = 2
                # Show response scores
                responses = Response.query.filter(
                    and_(Response.r_num <= round_number, Response.q_num <= question_number))
                for response in responses:
                    response.hidden = 0

            elif next_question is not None:
                # Next question
                question_number += 1
                if done == 2:
                    # Move to next answer but don't reveal yet
                    done = 1
            else:
                if not done and round_number > 0:
                    # Round done; Start going through answers
                    done = 1
                    question_number = 0
                else:
                    # Next round
                    next_question = Questions.query.filter(
                        and_(Questions.r_num == round_number + 1, Questions.q_num == 1)).one_or_none()
                    if next_question is not None:
                        round_number += 1
                        question_number = 0
                        done = 0

        elif request.form.get('prev') is not None:
            # Move quiz backwards
            prev_question = Questions.query.filter(
                and_(Questions.r_num == round_number, Questions.q_num == question_number - 1)).one_or_none()
            if done == 2:
                done = 1
            elif prev_question is not None or question_number == 1:
                # Previous question or restart round
                question_number -= 1
                if done:
                    if question_number != 0:
                        # Last answer is already revealed
                        done = 2
                    else:
                        # Restart round
                        done = 1
            else:
                if done:
                    # Reopen round
                    prev_question = Questions.query.filter(Questions.r_num == round_number).order_by(
                        Questions.q_num.desc()).one()
                    done = 0
                    question_number = prev_question.q_num
                else:
                    if round_number <= 1:
                        # Back to waiting for quiz to start
                        round_number = 0
                    else:
                        # Back to previous round's answers
                        prev_question = Questions.query.filter(Questions.r_num == round_number - 1).order_by(
                            Questions.q_num.desc()).first()
                        done = 2
                        round_number -= 1
                        question_number = prev_question.q_num

        elif request.form.get('kick_players') is not None:
            db.session.execute('DELETE FROM players')
        elif request.form.get('reset_state') is not None:
            # db.session.execute('DELETE FROM state')
            round_number = 0
            question_number = 0
            done = 0
            # No need as these values will be updated after the next block.
            # cur.execute('INSERT INTO state (r_num) VALUES (0)')
        elif request.form.get('reset_responses') is not None:
            db.session.execute('DELETE FROM responses')
            # update_scores()

        state.r_num = round_number
        state.q_num = question_number
        state.done = done
        db.session.commit()

    if question_number > 0:
        question = Questions.query.filter(
            and_(Questions.r_num == round_number, Questions.q_num == question_number)).one()
    else:
        question = None

    if done and question_number > 0:
        # Show question-scoring tools
        responses = Response.query.filter(
            and_(Response.r_num == round_number, Response.q_num == question_number)).all()
    else:
        responses = None

    if request.method == 'POST' and request.form.get('update_scores'):
        for response in responses:
            response.score = request.form['resp_' + response.name]
        db.session.commit()

        # Update responses so that control page shows the right scores
        responses = Response.query.filter(
            and_(Response.r_num == round_number, Response.q_num == question_number)).all()

    return render_template('control.html', responses=responses, question=question)


def import_questions_from_stream(stream):
    """
    Import questions from a spreadsheet into the database.
    :param stream:
    :return:
    """
    db.session.execute('DELETE FROM questions')
    try:
        r_num = None
        q_num = None
        for line in stream:
            line = line.decode("utf-8")[:-1]
            if line.lower().startswith('round'):
                # New round
                r_num = int(line.split(',')[0][5:])
                q_num = 1
                continue
            elif r_num is None:
                # No rounds started => Ignore line
                continue
            line_elements = line.split(',')
            q_type = line_elements[0]
            q_score = line_elements[1]
            q_text = line_elements[2]
            q_answer = line_elements[3]

            def filter_string(string):
                for i, char in enumerate(string):
                    if char == ':':
                        if string[i - 1] == '\\':
                            string.pop[i - 1]
                        else:
                            string = string[:i] + ',' + string[i + 1:]
                return string

            q_answer = filter_string(q_answer)

            question = Questions(r_num=r_num, q_num=q_num, question=q_text, answer=q_answer, score=q_score)
            if q_type.lower() == 'entry':
                question.type = q_type.lower()
            elif q_type.lower() == 'choice':
                question.type = q_type.lower()
                question.choices = filter_string(line_elements[4])
            else:
                # If the question type is unrecognised then bail out of the import.
                raise RuntimeError('Unrecognized question type')
            db.session.add(question)
            q_num += 1

        db.session.commit()
        return True

    except Exception as e:
        print(e)
        return False


@quiz.route('/upload_questions', methods=['GET', 'POST'])
@admin_only
def upload_questions():
    success = None
    questions = None
    if 'questions_file' in request.files:
        q_file = request.files['questions_file']
        success = import_questions_from_stream(q_file.stream)
        if success:
            questions = Questions.query.filter().all()

    return render_template('upload_questions.html', success=success, questions=questions)


@quiz.route('/login', methods=['GET', 'POST'])
def login():
    """
    Used to log a user in.  If they are not recognised or they've been away too long they will be
    created in the database.  No strict logins with authentication for this application as yet.
    It's just trying to get some players and run a quiz.
    :return:
    """
    # The caller wants to see the login page.
    if request.method == 'GET':
        return render_template('login.html')

    # The caller is sending a login request.
    if request.method == 'POST' and 'name' in request.form:
        name = request.form['name']

        player = Player.query.filter(Player.name == name).one_or_none()
        if player is None or (time.time() - player.last_seen) > 4 or name == session.get('name'):
            # Player name is available so log them in
            print('Login from', request.remote_addr, 'as', name)
            if player is None:
                # If the name is new, create a new player
                player = Player(name=name, score=0, last_seen=int(time.time()))
                db.session.add(player)
                db.session.commit()
            session['name'] = name
            return redirect(url_for('quiz.main'))
        else:
            # Player name is taken
            return 'This user is already logged in!'


@quiz.route('/')
def main():
    """
    The root page.  It checks to see if you are already logged in and directs you appropriately.
    If the quiz master id is used the user will be redirected to the control page.
    Otherwise the user will see the quiz itself.
    :return:
    """
    # If we know the caller's name check for admin otherwise show the quiz.
    if 'name' in session:
        # If the admin is signing in then go straight to control as they are not a player.
        if session['name'] == current_app.config['SECRET_ADMIN_NAME']:
            return redirect(url_for('quiz.control'))

        return render_template('main.html', name=session['name'])

    return redirect(url_for('quiz.login'))
