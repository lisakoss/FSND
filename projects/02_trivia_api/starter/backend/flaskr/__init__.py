import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection):
  page = request.args.get('page', 1, type=int)
  start = (page - 1) * 10
  end = start + 10

  formatted_questions = [question.format() for question in selection]

  return formatted_questions[start:end]

def get_random_question(category_questions, total_questions):
  return category_questions[random.randint(0, total_questions - 1)]

def check_question(random_question, previous_questions):
  used = False
  for question_id in previous_questions:
    if question_id == random_question.id:
      used = True
    
  return used

def create_app(test_config=None):
  # create and configure the app
  app = Flask(__name__)
  setup_db(app)
  CORS(app, resouces={r"*/api/*": {"origins": '*'}})
  
  @app.after_request
  def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
    return response 

  @app.route('/api/categories')
  def get_categories():
    categories = Category.query.all()
    formatted_categories = [category.format() for category in categories]

    return jsonify({
      'success': True,
      'categories': formatted_categories
    })

  @app.route('/api/questions')
  def get_questions():
    questions = Question.query.all()
    formatted_questions = paginate_questions(request, questions)

    categories = Category.query.all()
    formatted_categories = [category.format() for category in categories]

    return jsonify({
      'success': True,
      'questions': formatted_questions,
      'total_questions': len(questions),
      'current_category': 'none',
      'categories': formatted_categories
    })

  @app.route('/api/questions/<int:question_id>', methods=['DELETE'])
  def delete_question(question_id):
    try:
      question = Question.query.filter_by(id=question_id).one_or_none()

      if question is None:
        abort(404)

      question.delete()
      questions = Question.query.order_by(Question.id).all()
      formatted_questions = paginate_questions(request, questions)

      return jsonify({
        'success': True,
        'deleted': question_id,
        'questions': formatted_questions,
        'total_questions': len(Question.query.all())
      })

    except:
      abort(422)

  @app.route('/api/questions', methods=['POST'])
  def create_question():
    body = request.get_json()

    # check if request is for a search or for the creation of new question
    if body.get('searchTerm') != None:
      search_term = body.get('searchTerm')

      try:
        questions = Question.query.filter(Question.question.ilike(f'%{search_term}%')).all()
        formatted_questions = paginate_questions(request, questions)

        return jsonify({
          'success': True,
          'questions': formatted_questions,
          'total_questions': len(questions) # only want pagination for search results
        })

      except:
        abort(422)

    else:
      question = body.get('question')
      answer = body.get('answer')
      difficulty = body.get('difficulty')
      category = body.get('category')

      # all fields are required to submit a new question
      if ((question == '') or (answer == '') 
          or (difficulty == '') or (category == '')):
        abort(422)

      try:
        question = Question(question=question, answer=answer, 
                            difficulty=difficulty, category=category)
        question.insert()

        questions = Question.query.order_by(Question.id).all()
        formatted_questions = paginate_questions(request, questions)

        return jsonify({
          'success': True,
          'created': question.id,
          'questions': formatted_questions,
          'total_questions': len(Question.query.all())
        })

      except:
        abort(422)

  @app.route('/api/categories/<int:category_id>/questions')
  def get_questions_by_category(category_id):
    category = Category.query.filter_by(id=category_id).first()
    questions = Question.query.filter_by(category=category_id).all()
    formatted_questions = paginate_questions(request, questions)

    return jsonify({
      'success': True,
      'questions': formatted_questions,
      'current_category': category.type,
      'total_questions': len(Question.query.all())
    })

  @app.route('/api/quizzes', methods=['POST'])
  def get_quiz_questions():
    body = request.get_json()
    previous_questions = body.get('previous_questions')
    quiz_category = body.get('quiz_category')

    if quiz_category["type"] != "click":
      category_questions = Question.query.filter_by(category=str(int(quiz_category['id']) + 1)).all()
    else:
      category_questions = Question.query.all()

    total_questions = len(category_questions)

    # return if all questions have been answered 
    if total_questions == len(previous_questions):
      return jsonify({
        'success': True
      })

    random_question = get_random_question(category_questions, len(category_questions))

    while (check_question(random_question, previous_questions)):
      random_question = get_random_question(category_questions, len(category_questions))

    return jsonify({
      'success': True,
      'question': random_question.format()
    })

  '''
  @TODO: 
  Create error handlers for all expected errors 
  including 404 and 422. 
  '''
  
  return app

    