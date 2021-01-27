from flask import Flask, Blueprint
from flask_restful import Resource, Api, url_for

from .resources.hello import HelloWorld
from .resources.todo import Todo, TodoList

app = Flask(__name__)
api_bp = Blueprint('api', __name__)
api = Api(api_bp)


api.add_resource(HelloWorld, '/api/', '/api/hello')
api.add_resource(TodoList, '/api/todos')
api.add_resource(Todo, '/api/todos/<todo_id>')

app.register_blueprint(api_bp)
