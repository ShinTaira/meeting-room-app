# app.py (データベース設定を統合したバージョン)

import os # ★追加
from datetime import datetime # ★移動・確認
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy # ★追加
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin # ★UserMixinを追加
from werkzeug.security import generate_password_hash, check_password_hash # ★パスワードのハッシュ化ツール

# ▼▼▼ アプリケーションの基本設定 ▼▼▼
app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here' # このキーは安全なものに変更してください

# ▼▼▼ ★★★★★ ここからデータベース設定を追加 ★★★★★ ▼▼▼

# Renderで設定した環境変数(DATABASE_URL)を読み込む
database_url = os.environ.get('DATABASE_URL')

# RenderのDB URLは 'postgres://' で始まるため、SQLAlchemy推奨の 'postgresql://' に置換
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# データベース接続設定
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# データベースを扱うためのオブジェクトを作成
db = SQLAlchemy(app)


# ▼▼▼ ★★★★★ データベースの「設計図」(モデル)を定義 ★★★★★ ▼▼▼

# --- Userモデル (ログイン情報などを保存するテーブルの設計図) ---
# flask_loginが使えるように UserMixin を継承します
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# --- Bookingモデル (予約情報を保存するテーブルの設計図) ---
class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False) # 目的(purpose)をtitleとします
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    # ユーザーとの関連付け (どのユーザーが予約したか)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('bookings', lazy=True))


# ▼▼▼ ★★★★★ 最初の1回だけテーブルを自動作成するコード ★★★★★ ▼▼▼
with app.app_context():
    db.create_all()

# ----------------------------------------------------------------

# ▼▼▼ これ以降は、既存のコードを新しいデータベースを使うように少しずつ修正していきます ▼▼▼
# (今回はまず設定の統合だけ行い、ロジックの修正は次のステップで行います)

# --- Flask-Loginの設定 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "このページにアクセスするにはログインが必要です。"

# 既存のReservationSystemは後で消しますが、今はエラーにならないよう残しておきます
from SpinTechnologyMeetingRoomBookingSystemApp import ReservationSystem
system = ReservationSystem()

@login_manager.user_loader
def load_user(user_id):
    # ★★★【要修正】後でデータベースからユーザーを読み込むように変更します
    # return User.query.get(int(user_id))
    user_data = system.find_user_by_id(user_id) # 今は仮で元のコードを残します
    if user_data:
        # Userクラスの初期化方法が変わったため、仮の修正
        temp_user = User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
        return temp_user
    return None


# --- 認証ルート ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # ★★★【要修正】後でデータベースからユーザーを探すように変更します
        # user = User.query.filter_by(username=username).first()
        # if user and check_password_hash(user.password_hash, password):
        #     login_user(user)
        #     return redirect(url_for('index'))
        user_data = system.find_user_by_username(username) # 今は仮で元のコードを残します
        if user_data and check_password_hash(user_data['password_hash'], password):
            temp_user = User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
            login_user(temp_user)
            return redirect(url_for('index'))
        
        flash('ユーザー名またはパスワードが正しくありません。', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # ★★★【要修正】後でデータベースでユーザー名の重複を確認するように変更します
        # if User.query.filter_by(username=username).first():
        #    flash('そのユーザー名は既に使用されています。', 'error')
        # else:
        #    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        #    new_user = User(username=username, password_hash=hashed_password)
        #    db.session.add(new_user)
        #    db.session.commit()
        #    flash('登録が完了しました。ログインしてください。', 'success')
        #    return redirect(url_for('login'))
        if system.find_user_by_username(username): # 今は仮で元のコードを残します
            flash('そのユーザー名は既に使用されています。', 'error')
        else:
            system.add_user(username, password) # 本来はハッシュ化してDBに保存
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


# ...以降の /logout, /, /reserve などのルートは、今はそのままにしておきます...
# (コードが長くなるため省略しますが、ご自身の元のコードをそのまま使ってください)
# (次のステップで、これらの関数の中身を一つずつデータベースを使うように修正します)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# (これより下のルートの関数は、ご自身のファイルの内容をそのままコピーして貼り付けてください)
# @app.route('/')
# ...
# if __name__ == '__main__':
# ...