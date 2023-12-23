from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField
from wtforms.validators import DataRequired, URL, Email, Length
from flask_ckeditor import CKEditorField

##WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    category = SelectField("Category", choices=[('Movies', 'Movies'), ('Musics', 'Musics'), ('Topics', 'Topics')])
    img_url = StringField("Blog Image URL")
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class CommentForm(FlaskForm):
    comment_text = CKEditorField("", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")