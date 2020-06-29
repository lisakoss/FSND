import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

# determines which questions to show based on page number
def paginate_questions(request, selection):
  page = request.args.get('page', 1, type=int)
  start = (page - 1) * 10
  end = start + 10

  formatted_questions = [question.format() for question in selection]

  return formatted_questions[start:end]

# return a random question from the given questions
def get_random_question(category_questions, total_questions):
  return category_questions[random.randint(0, total_questions - 1)]

# check if question has already been answered by the user
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
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response 

  # handles GET requests for all categories
  @app.route('/api/categories')
  def get_categories():
    categories = Category.query.all()
    formatted_categories = [category.format() for category in categories]

    # abort if no categories found
    if len(formatted_categories) == 0:
      abort(404)

    return jsonify({
      'success': True,
      'categories': formatted_categories
    })

  # handles GET requests for all questions
  @app.route('/api/questions')
  def get_questions():
    questions = Question.query.all()
    formatted_questions = paginate_questions(request, questions)

    categories = Category.query.all()
    formatted_categories = [category.format() for category in categories]

    # abort if no questions found
    if len(formatted_questions) == 0:
      abort(404)

    return jsonify({
      'success': True,
      'questions': formatted_questions,
      'total_questions': len(questions),
      'current_category': 'none',
      'categories': formatted_categories
    })

  # handles DELETE request for given question ID
  @app.route('/api/questions/<int:question_id>', methods=['DELETE'])
  def delete_question(question_id):
    try:
      question = Question.query.filter_by(id=question_id).one_or_none()

      # abort if question does not exist
      if question is None:
        abort(422)

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

  # handle POST requests for new questions & search terms
  @app.route('/api/questions', methods=['POST'])
  def create_question():
    body = request.get_json()

    # check if request is for a search or for the creation of new question
    if body.get('searchTerm') != None:
      search_term = body.get('searchTerm')

      try:
        questions = Question.query.filter(Question.question.ilike(f'%{search_term}%')).all()
       
        # no search results found
        if len(questions) == 0:
          abort(404
          )

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

      # all fields are required to submit a new question, abort otherwise
      if ((question is None or question == '') or (answer is None or answer == '') 
          or (difficulty is None or difficulty == '') or (category is None or category == '')):
        abort(400)

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

  # handles GET request for questions in a given category
  @app.route('/api/categories/<int:category_id>/questions')
  def get_questions_by_category(category_id):
    category = Category.query.filter_by(id=category_id).one_or_none()

    # abort if category does not exist
    if category is None:
      abort(404)

    questions = Question.query.filter_by(category=category_id).all()
    formatted_questions = paginate_questions(request, questions)

    return jsonify({
      'success': True,
      'questions': formatted_questions,
      'current_category': category.type,
      'total_questions': len(Question.query.all())
    })

  # handles POST requests for taking a new quiz
  @app.route('/api/quizzes', methods=['POST'])
  def get_quiz_questions():
    body = request.get_json()
    previous_questions = body.get('previous_questions')
    quiz_category = body.get('quiz_category')

    # abort if category or previous questions is not found
    if (quiz_category is None) or (previous_questions is None):
      abort(400)

    # determine if the user wants to take a quiz with questions from all categories
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

    # continue generating a random question until a new one is found
    while (check_question(random_question, previous_questions)):
      random_question = get_random_question(category_questions, len(category_questions))

    return jsonify({
      'success': True,
      'question': random_question.format()
    })

  # error handlers for all errors
  @app.errorhandler(400)
  def bad_request(error):
    return jsonify({
        "success": False, 
        "error": 400,
        "message": "Bad request"
        }), 400

  @app.errorhandler(404)
  def not_found(error):
    return jsonify({
        "success": False, 
        "error": 404,
        "message": "Not found"
        }), 404

  @app.errorhandler(422)
  def unprocessable(error):
    return jsonify({
        "success": False, 
        "error": 422,
        "message": "Unprocessable"
        }), 422
  
  return app
