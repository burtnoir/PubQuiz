# PubQuiz
This is a simple web "pub quiz" interface written using the Python Flask interface.
The file 'manual.pdf' gives an idea of how it works.  The quizmaster login is _secadmin and there are no passwords for anyone as it is intended to be run locally at this point. 

### WARNING:
This code was not written with the intent of being scalable or extensible. It fundamentally does not support multiple concurrent games. Database access is mostly done using SQLAlchemy, the interface uses basic Javascript (no JQuery). Although there was an attempt at basic security, this web service is likely riddled with critical vulnerabilities and should NOT be hosted publicly.
