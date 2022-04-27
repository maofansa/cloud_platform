"""
    登录注册表单处理
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from app.models import User


class LoginForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired()])
    password = PasswordField("密码", validators=[DataRequired()])
    remember_me = BooleanField("记住我")
    submit = SubmitField("登录")


class RegistrationForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField("密码", validators=[DataRequired()])
    password2 = PasswordField(
        "重复密码", validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField("注册")
    # Test
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("用户名已被注册。")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("邮箱已被注册。")
