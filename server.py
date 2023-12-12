from flask import Flask, render_template, redirect, url_for, request, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps
from forms import CreatePostForm, LoginForm, RegisterForm, CommentForm
from sqlalchemy.orm import relationship


# # Delete this code:
# import requests
# posts = requests.get("https://api.npoint.io/43644ec4f0013682fc0d").json()

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///default.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.Text)
    like_num = db.Column(db.Integer)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    # ***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()


@app.route("/")
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route("/<name>")
def get_category(name):
    posts = BlogPost.query.where(BlogPost.category==name.capitalize())
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:index>")
def show_post(index):
    posts = BlogPost.query.all()
    requested_post = BlogPost.query.get(index)
    for blog_post in posts:
        if int(blog_post.id) == index:
            requested_post = blog_post
    return render_template("post.html", post=requested_post)


#Create owner/owner/admin-only decorator
def owner_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(args)
        #If id is not 1 then return abort with 403 error
        if current_user.is_authenticated:
            if current_user.id != 1:
                return abort(403)
        else:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@owner_only
def edit_post(post_id):
    post = db.session.query(BlogPost).get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        category=post.category,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.category = edit_form.category.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    return render_template("make-post.html", form=edit_form, is_edit=post_id)


@app.route("/new-post", methods=["POST", "GET"])
@login_required
def new_post():
    if current_user:
        form = CreatePostForm()
        if form.validate_on_submit():
            new_blog_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                category=form.category.data,
                author=current_user,
                like_num=0,
                img_url=form.img_url.data,
                body=form.body.data,
                date=datetime.datetime.now().strftime("%d/%m/%y")
            )
            db.session.add(new_blog_post)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
        return render_template("make-post.html", form=form)
    else:
        return redirect(url_for('login'))


@app.route("/delete/<post_id>", methods=["GET", "DELETE"])
@owner_only
def delete_post(post_id):
    post = db.session.query(BlogPost).get(post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/categories")
def categories():
    return render_template("categories.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist
        if not user:
            error = "That email does not exist, please try again."
            # return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            error = 'Password incorrect, please try again.'
            # return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, error=error)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == "POST":
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            return redirect(url_for('login'))
        else:
            hash_and_salted_password = generate_password_hash(
                request.form.get('password'),
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                email=email,
                name=request.form.get('name'),
                surname=request.form.get('surname'),
                phone=request.form.get('phone'),
                password=hash_and_salted_password,
            )
            db.session.add(new_user)
            db.session.commit()

            # Log in and authenticate user after adding details to database.
            login_user(new_user)

            return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form,logged_in=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

@app.route("/get_all_users")
def get_all_users():
    users = User.query.all()
    for user in users:
        print(f"User {user.id}: {user.name} {user.surname}, Email: {user.email}, Phone: {user.phone}")
    return "Users printed in the terminal."

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
