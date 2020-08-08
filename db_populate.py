from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from PubQuiz import models, create_app

app = create_app()

# This script
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Session = sessionmaker(bind=engine)

session = Session()

session.execute('DELETE FROM state')
session.execute('DELETE FROM players')
session.execute('DELETE FROM questions')
session.execute('DELETE FROM responses')

state = models.State(r_num=0, q_num=0, done=0)
session.add(state)

player = models.Player(name=app.config['SECRET_ADMIN_NAME'], score=0, last_seen=0)
session.add(player)

questions = [(1, 1, 'Operation Tamarisk was one of the most successful of the whole cold war. What did it involve?',
              'choice',
              'Used toilet paper,Sleeping with the children of officials,Stealing classified dust,Bringing sugar back into West Berlin',
              'Used toilet paper', 2),
             (1, 2, 'Why would James Bond not be accepted into GCHQ as a spy?', 'entry', '',
              'Alcoholic,No emotional intelligence', 3),
             (1, 3, 'How did a woman get across the Berlin Wall?', 'choice',
              'Parachuting across,Sewn into a coat,Sewn into a car seat,Pretended to be a statue',
              'Sewn into a car seat', 2),
             (2, 1, 'Australian adults are more cautious drivers when this person/ object is in the back seat.',
              'choice', 'Their child,Their weekly shopping,A dog,A pavlova', 'A pavlova', 2),
             (2, 2, 'What new feature was added to Volvos in 2007?', 'choice',
              'An ejecting disk to identify the car in case of a hit and run,A heart monitor linked to the car key,Voice activate functions,A coffee machine',
              'A heart monitor linked to the car key', 2),
             (
                 3, 1, 'Whose "Voodoo Queen" Grandmother', 'choice',
                 'Keanu Reeves,Whoopi Goldberg,Ringo Star,Seth Rogan',
                 'Ringo Star', 2),
             (3, 2, 'What change did The Beatles cause the Japanese Police Force to make?', 'choice',
              'White gloves,Louder megaphones,English language curriculum,Recruitment jingle', 'White gloves', 2),
             (3, 3, 'What did the Beatles\' disgruntled manager say that McCartney did to get him deported?', 'choice',
              'Sex with minor,Burned a condom,Urinated on the American flag,Streaked through a restaurant',
              'Burned a condom', 2),
             (3, 4, 'Who did Ringo Star voice before his fame?', 'choice',
              'Blue Peter,Postman Pat,Bob the Builder,Thomas the Tank Engine', 'Thomas the Tank Engine', 2),
             (4, 1, 'Which birds live in open yet very committed relationships?', 'choice',
              'Flamingo,Penguin,Pigeon,Albatross', 'Albatross', 2),
             (4, 2, 'Up to how long can baby albatross\' take to \'pip\'?', 'entry', '', 'seven', 2),
             (4, 3, 'What invasive species arrived on Goth Island and started to eat the Tristan Albatros?', 'choice',
              'rats,beetles,snakes,mice', 'mice', 2),
             (4, 4, 'What animal did Western explorers initially think Albatross\' were?', 'choice',
              'platypus,sheep,pigeon,cat', 'sheep', 2),
             (5, 1, 'Which film / TV show are these?', 'entry', '', 'wow exciting!', 0),
             (5, 2, 'Roman goddess of women and marriage', 'entry', '', 'Juno', 2),
             (5, 3, 'Acquaintances', 'entry', '', 'friends', 2),
             (5, 4, 'Good weather cream cheese', 'entry', '', 'Always sunny in Philadelphia', 2),
             (5, 5, '2(3a-17)=8', 'entry', '', 'Seven,7', 2),
             (5, 6, 'No use', 'entry', '', 'Pointless', 2),
             (5, 7, 'More weird objects', 'entry', '', 'Stranger Things', 2),
             (5, 8, 'Subservient for 4380 days', 'entry', '', '12 years a slave', 2)
             ]

for item in questions:
    question = models.Questions(r_num=item[0], q_num=item[1], question=item[2], type=item[3], choices=item[4],
                                answer=item[5], score=item[6])
    session.add(question)

session.commit()
