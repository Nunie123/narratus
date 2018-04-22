from configparser import ConfigParser
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# import config file to global object
config = ConfigParser()
config_file = '/Users/ednunes/dev/narratus/backend/config.ini'
config.read(config_file)

# instantiate flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.get('flask', 'secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('flask', 'production_db_uri')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = config.get('flask', 'jwt_secret_key')
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
jwt = JWTManager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
aws_key_id = config.get('flask', 'aws_key_id')


from backend.app import routes, models


# if __name__ == '__main__':
#     app.run(debug = True)
