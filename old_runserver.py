from PubQuiz import create_app
quiz = create_app()
quiz.run(debug=True, use_debugger=True, use_reloader=False, host='192.168.1.13', port=5000)


