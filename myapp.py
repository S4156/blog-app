from flask import Flask, render_template,request,redirect,flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_login import UserMixin,LoginManager,login_user,login_required,logout_user
from werkzeug.security import generate_password_hash,check_password_hash
import pytz
import os
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv

load_dotenv()  # .envファイルを読み込む

app = Flask(__name__)

#②ログイン管理システム
login_manager=LoginManager()
login_manager.init_app(app)

if app.debug:
  #①いったんランダム。本番環境で書き換える
  app.config["SECRET_KEY"]=os.urandom(24)
else:
  app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY")
  SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL").replace("postgres://","postgresql+psycopg://")
db=SQLAlchemy()
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
db.init_app(app)
migrate=Migrate(app,db)

class Post(db.Model):
  id=db.Column(db.Integer,primary_key=True)
  title=db.Column(db.String(100),nullable=False)
  body=db.Column(db.String(1000),nullable=False)
  tokyo_timezone=pytz.timezone('Asia/Tokyo')
  created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=datetime.now(tokyo_timezone))
  img_name=db.Column(db.String(100),nullable=True)

class User(UserMixin,db.Model):
  id=db.Column(db.Integer,primary_key=True)
  username=db.Column(db.String(50),nullable=False,unique=True)
  password=db.Column(db.String(200),nullable=False)

#③現在のユーザーを識別するための関数
@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))

@app.route("/")
def index():
  posts=Post.query.all()
  return render_template("index.html",posts=posts)

@app.route("/<int:post_id>/readMore")
def readMore(post_id):
  post=Post.query.get(post_id)
  return render_template("readMore.html",method="GET",post=post)

@app.route("/admin")
@login_required
def admin():
  # posts=Post.query.all()
  posts=Post.query.order_by(db.desc("created_at")).all()
  print(posts)
  return render_template("admin.html",posts=posts)


@app.route("/create",methods=['GET','POST'])
@login_required
def create():
  if request.method=="POST":
    title=request.form.get("title")
    body=request.form.get("body")
    file=request.files["img"]
    filename = file.filename
    try:
      image = Image.open(file.stream)
      image.verify()  # 画像として読み込めるか確認（破損していてもここで失敗）
    except UnidentifiedImageError:
      flash("有効な画像ファイルを選択してください", "error")
      return redirect("/create")
    # file=request.files["img"]
    file.stream.seek(0)
    post=Post(title=title,body=body,img_name=filename)
    save_path=os.path.join(app.static_folder,"img",filename)
    file.save(save_path)
    db.session.add(post)
    db.session.commit()
    return redirect("/admin")
  elif request.method=="GET":
    return render_template("create.html",method="GET")

@app.route("/<int:post_id>/update",methods=['GET','POST'])
@login_required
def update(post_id):
  post=Post.query.get(post_id)
  if request.method=="POST":
    post.title=request.form.get("title")
    post.body=request.form.get("body")
    # tokyo_timezone=pytz.timezone('Asia/Tokyo')
    # post.created_at=datetime.now(tokyo_timezone)
    db.session.commit()
    return redirect("/admin")
  elif request.method=="GET":
    return render_template("update.html",method="GET",post=post)

@app.route("/<int:post_id>/delete",methods=['GET','POST'])
@login_required
def delete(post_id):
  post=Post.query.get(post_id)
  db.session.delete(post)
  db.session.commit()
  return redirect("/admin")

@app.route("/signup",methods=['GET','POST'])
def signup():
    if request.method=="POST":
      username=request.form.get("username")
      password=request.form.get("password")
      hashed_pass=generate_password_hash(password)
      user=User(username=username,password=hashed_pass)
      db.session.add(user)
      db.session.commit()
      return redirect("/login")
    elif request.method=='GET':
      return render_template("signup.html")
  
@app.route("/login", methods=['GET','POST'])
def login():
    if request.method=="POST":
      #ユーザー名とパスワードの受け取り
      username=request.form.get("username")
      password=request.form.get("password")
      #ユーザー名をもとにデータベースから情報を取得
      user=User.query.filter_by(username=username).first()
      #入力パスワードとデータベースのパスワードが一致しているか確認
      #一致していればログインさせて管理画面へリダイレクトさせる
      if check_password_hash(user.password,password=password):
        login_user(user)
        return redirect("/admin")
      #間違っている場合、エラー文と共にログイン画面へリダイレクトさせる
      else:
        return redirect("/login",msg="ユーザー名、パスワードが違います")
    elif request.method=='GET':
      return render_template("login.html",msg="")
    
@app.route("/logout")
@login_required
def logout():
  logout_user()
  return redirect("/login")