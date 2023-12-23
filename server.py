from flask import render_template, redirect, url_for, request, abort, flash
from flask_ckeditor import CKEditor
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreatePostForm, CommentForm
from database import app, db, User, BlogPost, Comment

import datetime
from functools import wraps

ckeditor = CKEditor(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)

CATEGORIES = ['movies', 'topics', 'musics']

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/", methods=["GET"])
def get_all_posts():
    posts = BlogPost.query.order_by(BlogPost.like_num.desc()).all()
    return render_template("index.html", all_posts=posts)

@app.route("/category/<name>", methods=["GET", "POST"])
def get_category(name):
    if name in CATEGORIES:
        posts = BlogPost.query.filter_by(category=name.capitalize()).order_by(BlogPost.like_num.desc()).all()
        return render_template(f"{name.lower()}.html", all_posts=posts)
    else:
        return redirect(url_for('get_all_posts'))


#Create owner/owner/admin-only decorator
def owner_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        post = db.session.query(BlogPost).get(int(kwargs['post_id']))
        try:
            comment = db.session.query(Comment).get(int(kwargs['comment_id']))
            if current_user.id != 1 and current_user.id != comment.comment_author.id:
                return abort(403)
        except:
            if current_user.is_authenticated:
                if current_user.id != 1 and current_user.id != post.author.id:
                    return abort(403)
            else:
                return abort(403)
            return f(*args, **kwargs)

        #If id is not 1 then return abort with 403 error
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route("/new-post", methods=["POST", "GET"])
def new_post():
    if current_user.is_authenticated:
        form = CreatePostForm()
        if form.validate_on_submit():
            new_blog_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                category=form.category.data,
                author=current_user,
                like_num=0,
                likes="",
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

@app.route("/post/<int:index>", methods=['GET', 'POST'])
def show_post(index):
    form = CommentForm()
    requested_post = BlogPost.query.get(index)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post,
            like_num=0,
            likes=""
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", index=requested_post.id))
    return render_template("post.html", post=requested_post, form=form, current_user=current_user)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST", "PUT"])
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
        return redirect(url_for('show_post', index=post_id))
    return render_template("make-post.html", form=edit_form, is_edit=post_id)

@app.route("/delete/<int:post_id>/<page>", methods=["GET", "DELETE"])
@owner_only
def delete_post(post_id, page):
    post = db.session.query(BlogPost).get(post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
    if page == "home":
        return redirect(url_for("get_all_posts"))
    elif page == "profile":
        return redirect(url_for("show_profile", user_id=post.author_id))
    return redirect(url_for('get_all_posts'))

@app.route("/like/post/<int:post_id>/<page>", methods=["GET", "POST", "PUT","DELETE"])
@login_required
def like_post(post_id, page):
    post = db.session.query(BlogPost).get(post_id)
    if post.likes == "":
        post.likes = f"{current_user.id}"
    else:
        liked_users = post.likes.split(",")
        if str(current_user.id) in liked_users:
            if f",{current_user.id}" in post.likes:
                post.likes = post.likes.replace(f",{current_user.id}", "")
            elif f"{current_user.id}," in post.likes:
                post.likes = post.likes.replace(f"{current_user.id},", "")
            else:
                post.likes = post.likes.replace(f"{current_user.id}", "")
            post.like_num -= 1
        else:
            post.likes = post.likes + f",{current_user.id}"
            post.like_num += 1
    if post.likes.split(",")[0] == "":
        post.like_num = 0
    else:
        post.like_num = len(post.likes.split(","))
    db.session.commit()
    if page == "home":
        return redirect(url_for("get_all_posts"))
    elif page == "profile":
        return redirect(url_for("show_profile", user_id=post.author_id))
    return redirect(url_for("show_post", index=post_id))


@app.route("/post/<int:post_id>/delete-comment/<int:comment_id>", methods=['GET', 'DELETE', 'POST'])
@owner_only
def delete_comment(post_id, comment_id):
    comment = db.session.query(Comment).get(comment_id)
    if comment:
        db.session.delete(comment)
        db.session.commit()
    return redirect(url_for("show_post", index=post_id))

@app.route("/like/comment/<int:comment_id>/<page>", methods=["GET", "POST", "PUT","DELETE"])
@login_required
def like_comment(comment_id, page):
    comment = db.session.query(Comment).get(comment_id)
    if comment.likes == "":
        comment.likes = f"{current_user.id}"
    else:
        liked_users = comment.likes.split(",")
        if str(current_user.id) in liked_users:
            if f",{current_user.id}" in comment.likes:
                comment.likes = comment.likes.replace(f",{current_user.id}", "")
            elif f"{current_user.id}," in comment.likes:
                comment.likes = comment.likes.replace(f"{current_user.id},", "")
            else:
                comment.likes = comment.likes.replace(f"{current_user.id}", "")
            comment.like_num -= 1
        else:
            comment.likes = comment.likes + f",{current_user.id}"
            comment.like_num += 1
    if comment.likes.split(",")[0] == "":
        comment.like_num = 0
    else:
        comment.like_num = len(comment.likes.split(","))
    db.session.commit()
    return redirect(url_for("show_post", index=comment.post_id))


@app.route('/login', methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("femail")
        password = request.form.get("fpassword")
        user = User.query.filter_by(email=email).first()
        # Email doesn't exist
        if not user:
            error = "That email does not exist, please register."
            # return redirect(url_for('register'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            error = 'Password incorrect, please try again.'
            # return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", error=error)

@app.route('/register', methods=["GET", "POST"])
def register():
    # form = RegisterForm()
    if request.method == "POST":
        email = request.form.get('femail')
        if User.query.filter_by(email=email).first():
            return redirect(url_for('login'))
        else:
            hash_and_salted_password = generate_password_hash(
                request.form.get('fpassword'),
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                email=email,
                name=request.form.get('fname'),
                surname=request.form.get('fsurname'),
                phone=request.form.get('fphone'),
                password=hash_and_salted_password,
            )
            db.session.add(new_user)
            db.session.commit()

            # Log in and authenticate user after adding details to database.
            login_user(new_user)

            return redirect(url_for("get_all_posts"))

    return render_template("register.html", logged_in=current_user.is_authenticated)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/profile/<int:user_id>', methods=['GET', 'POST', 'DELETE'])
def show_profile(user_id):
    try:
        user = db.session.query(User).get(user_id)
        user_posts = BlogPost.query.filter_by(author_id=user_id).order_by(BlogPost.like_num.desc()).all()
        return render_template("profile.html", user=user, user_posts=user_posts)
    except:
        return redirect(url_for("get_all_posts"))


if __name__ == "__main__":
    app.run(debug=True)
