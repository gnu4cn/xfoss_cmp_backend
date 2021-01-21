from flask import Flask, Blueprint
from flask_restful import Resource, Api, url_for

from src.resources.hello import HelloWorld
from src.resources.todo import Todo, TodoList

app = Flask(__name__)
api_bp = Blueprint('api', __name__)
api = Api(api_bp)


api.add_resource(HelloWorld, '/')
api.add_resource(TodoList, '/todos')
api.add_resource(Todo, '/todos/<todo_id>')

app.register_blueprint(api_bp)
