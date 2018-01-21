from flask import Flask
from configparser import ConfigParser
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# import config file to global object
config = ConfigParser()
config_file = 'config.ini'
config.read(config_file)

# instantiate flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.get('flask','secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('flask','database_uri')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


from app import routes, models


# if __name__ == '__main__':
#     app.run(debug = True)
