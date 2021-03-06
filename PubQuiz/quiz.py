import time
from functools import wraps

from flask import Blueprint, render_template, request, session, abort, redirect, current_app, url_for, flash

from PubQuiz.models import Player, Questions, Response, State, Round
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

    quiz_round = Round.query.filter(Round.r_num == r_num).one()
    questions = Questions.query.filter(Questions.q_num <= q_num).join(Round).filter(Round.r_num == r_num).order_by(
        Questions.q_num).all()

    for question in questions:
        question.first_answer = question.answer.split(',')[0]

    responses = Response.query.filter(Response.player_id == player.id).join(Questions).join(Round).filter(
        Round.r_num == r_num).all()

    if state.done == 0:  # Active round
        answers = {}
        for r in responses:
            answers[r.q_num] = r.answer
        return render_template('quiz_round.html', players=players, name=name, now_time=now_time, quiz_round=quiz_round,
                               questions=questions, answers=answers, enumerate=enumerate)
    else:  # Completed round
        return render_template('quiz_round_done.html', players=players, name=name, now_time=now_time,
                               quiz_round=quiz_round, questions=questions, state=state)


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
            response = Response.query.filter(Response.player_id == player.id).join(Questions).filter(
                Questions.q_num == q_num).join(Round).filter(Round.r_num == r_num).one_or_none()

            # Only update response if it is new
            if response is None or response.answer != ans_val:
                # Auto-score new answer
                score = 0
                question = Questions.query.filter(Questions.q_num == q_num).join(Round).filter(
                    Round.r_num == r_num).one()
                for right_answer in question.answer.split(','):
                    if ans_val.lower() == right_answer.lower():
                        score = question.score
                        break

                # Commit response
                if response is None:
                    response = Response(question_id=question.id, q_num=q_num, player_id=player.id, name=player.name,
                                        answer=ans_val, score=score, hidden=1)
                    db.session.add(response)
                else:
                    response.answer = ans_val
                    response.score = score
                db.session.commit()
    return 'ok'


@quiz.route('/kick_players', methods=['POST'])
@admin_only
def kick_players():
    """
    Remove all the players.
    :return:
    """
    state = State.query.filter().one()
    db.session.execute('DELETE FROM players')
    db.session.commit()
    flash('Players Deleted', 'success')
    question, responses = get_question_and_response(state.done, state.q_num, state.r_num)
    return render_template('control.html', responses=responses, question=question)


@quiz.route('/reset_state', methods=['POST'])
@admin_only
def reset_state():
    """
    Reset the state back to the start of the quiz.
    :return:
    """
    state = State.query.filter().one()
    state.r_num = 0
    state.q_num = 0
    state.done = 0
    db.session.commit()
    flash('State Reset', 'success')
    # Back at the start so we are before the question and response stage.
    return render_template('control.html', responses=None, question=None)


@quiz.route('/reset_responses', methods=['POST'])
@admin_only
def reset_responses():
    """
    Clear the responses.
    :return:
    """
    state = State.query.filter().one()
    db.session.execute('DELETE FROM responses')
    db.session.commit()
    flash('Responses Reset', 'success')
    question, responses = get_question_and_response(state.done, state.q_num, state.r_num)
    return render_template('control.html', responses=responses, question=question)


@quiz.route('/update_scores', methods=['POST'])
@admin_only
def update_scores():
    """
    The quiz master has updated the scores so commit the changes to the database and redisplay the screen.
    :return:
    """
    state = State.query.filter().one()
    question, responses = get_question_and_response(state.done, state.q_num, state.r_num)

    for response in responses:
        response.score = request.form['resp_' + response.name]
    db.session.commit()
    flash('Scores Updated', 'success')

    # Update responses so that control page shows the right scores
    responses = Response.query.filter(Response.r_num == state.r_num, Response.q_num == state.q_num).all()

    return render_template('control.html', responses=responses, question=question)


@quiz.route('/control', methods=['GET', 'POST'])
@admin_only
def control():
    """
    Used by the quiz master to administer the quiz.
    It can be used to move the questions backwards and forwards.
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
                Questions.q_num == question_number + 1).join(Round).filter(Round.r_num == round_number).one_or_none()
            if done == 1 and question_number > 0:
                # Reveal answer
                done = 2
                # Show response scores
                responses = Response.query.join(Questions).filter(Questions.q_num <= question_number).join(
                    Round).filter(Round.r_num <= round_number).all()
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
                    next_question = Questions.query.filter(Questions.q_num == 1).join(Round).filter(
                        Round.r_num == round_number + 1).one_or_none()
                    if next_question is not None:
                        round_number += 1
                        question_number = 0
                        done = 0

        elif request.form.get('prev') is not None:
            # Move quiz backwards
            prev_question = Questions.query.filter(Questions.q_num == question_number - 1).join(Round).filter(
                Round.r_num == round_number).one_or_none()
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
                    prev_question = Questions.query.join(Round).filter(Round.r_num == round_number).order_by(
                        Questions.q_num.desc()).first()
                    done = 0
                    question_number = prev_question.q_num
                else:
                    if round_number <= 1:
                        # Back to waiting for quiz to start
                        round_number = 0
                    else:
                        # Back to previous round's answers
                        prev_question = Questions.query.join(Round).filter(
                            Round.r_num == round_number - 1).order_by(Questions.q_num.desc()).first()
                        done = 2
                        round_number -= 1
                        question_number = prev_question.q_num

        state.r_num = round_number
        state.q_num = question_number
        state.done = done
        db.session.commit()

    question, responses = get_question_and_response(done, question_number, round_number)

    return render_template('control.html', responses=responses, question=question)


def get_question_and_response(done, question_number, round_number):
    """
    Get the question and response objects given a question number and round number.
    TODO If we stored the question id then we would not need the round number here.
    :param done:
    :param question_number:
    :param round_number:
    :return:
    """
    if question_number > 0:
        question = Questions.query.filter(Questions.q_num == question_number).join(Round).filter(
            Round.r_num == round_number).one()
    else:
        question = None
    if done and question_number > 0:
        # Show question-scoring tools
        responses = Response.query.join(Questions).filter(Questions.q_num == question_number).join(Round).filter(
            Round.r_num == round_number).all()
    else:
        responses = None
    return question, responses


def import_questions_from_stream(stream):
    """
    Import questions from a spreadsheet into the database.
    :param stream:
    :return:
    """
    # TODO It might be nice to offer the ability to append new questions.
    # Clear down the existing questions before uploading new ones.
    db.session.execute('DELETE FROM questions')
    db.session.execute('DELETE FROM rounds')
    try:
        r_num = None
        q_num = None
        quiz_round = None
        for line in stream:
            line = line.decode("utf-8")[:-1]
            line_elements = line.split(',')
            if line.lower().startswith('round'):
                # New round
                r_num = int(line_elements[0][5:])
                q_num = 1
                quiz_round = Round(r_num=r_num, description=line_elements[1])
                db.session.add(quiz_round)
                db.session.commit()
                continue
            elif r_num is None:
                # No rounds started => Ignore line
                continue
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

            question = Questions(round_id=quiz_round.id, r_num=quiz_round.r_num, q_num=q_num, question=q_text,
                                 answer=q_answer, score=q_score)
            if q_type.lower() == 'entry':
                question.type = q_type.lower()
            elif q_type.lower() == 'choice':
                question.type = q_type.lower()
                question.choices = filter_string(line_elements[4])
            else:
                # If the question type is unrecognised then bail out of the import.
                raise RuntimeError('Unrecognized question type')
            db.session.add(question)
            db.session.commit()
            q_num += 1

        # Reset the game state now we have new questions.
        state = State.query.first()
        state.r_num = 0
        state.q_num = 0
        state.done = 0
        db.session.commit()

        return True

    except Exception as e:
        print(e)
        return False


@quiz.route('/upload_questions', methods=['GET', 'POST'])
@admin_only
def upload_questions():
    success = None
    quiz_rounds = None
    if 'questions_file' in request.files:
        q_file = request.files['questions_file']
        success = import_questions_from_stream(q_file.stream)
        if success:
            flash('Questions uploaded successfully!', 'success')
            quiz_rounds = Round.query.order_by(Round.r_num).all()

    return render_template('upload_questions.html', success=success, quiz_rounds=quiz_rounds)


@quiz.route('/login', methods=['GET'])
def login_start():
    """
    The caller wants to see the login page.
    :return:
    """
    if request.method == 'GET':
        return render_template('login.html')


@quiz.route('/login', methods=['POST'])
def login_user():
    """
    Used to log a user in.  If they are not recognised or they've been away too long they will be
    created in the database.  No strict logins with authentication for this application as yet.
    It's just trying to get some players and run a quiz.
    :return:
    """

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

    return redirect(url_for('quiz.login_start'))
