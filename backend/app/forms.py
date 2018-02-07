from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from wtforms.fields.html5 import EmailField
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email address already in use.')

class ConnectionForm(FlaskForm):
    label = StringField('Connection Name')
    db_type = SelectField('Database Type', choices=[(postgresql, Postgresql), (sqlite, SQLite)])
    host = StringField('Host')
    port = IntegerField('Port')
    username = StringField('Username')
    

class QueryForm(FlaskForm):
    pass

class ChartForm(FlaskForm):
    pass

class ReportForm(FlaskForm):
    pass

class PublicationForm(FlaskForm):
    pass

class ContactForm(FlaskForm):
    pass
