#coding:utf-8
from flask.ext.wtf import Form
from flask_pagedown.fields import PageDownField
from wtforms import StringField, SubmitField, TextAreaField,HiddenField
from wtforms.validators import DataRequired, Length, Email, Optional


class CommentForm(Form):
    name = StringField(u'昵称', validators=[DataRequired()])
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                            Email()])
    content = PageDownField(u'内容', validators=[DataRequired(), Length(1, 1024)])
    follow = HiddenField(validators=[DataRequired()])
    submit = SubmitField('提交')
