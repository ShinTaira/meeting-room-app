from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil.relativedelta import relativedelta
import datetime
import uuid
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')

# --- データベース設定 ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Flask-Loginの設定 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "このページにアクセスするにはログインが必要です。"
login_manager.login_message_category = "error"

# --- データベースモデル定義 ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    reservations = db.relationship('Reservation', backref='booker', lazy=True)

    def is_active(self):
        return True
    def get_id(self):
        return self.id
    def is_authenticated(self):
        return True
    def is_anonymous(self):
        return False

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purpose = db.Column(db.String(120), nullable=False)
    room_name = db.Column(db.String(80), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

# --- アプリケーションの初回起動時にデータベーステーブルを作成 ---
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

# --- 認証ルート ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
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
        if User.query.filter_by(username=username).first():
            flash('そのユーザー名は既に使用されています。', 'error')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- メインの予約システムルート ---
@app.route('/')
@app.route('/<date_str>')
@login_required
def index(date_str=None):
    if date_str is None:
        return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))
    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))
    
    limit_date = datetime.date.today() - datetime.timedelta(days=30)
    show_prev_link = target_date > limit_date
    rooms = ["会議室A", "会議室B", "会議室C", "大部屋"]
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 24) for m in (0, 30)]
    
    start_of_day = datetime.datetime.combine(target_date, datetime.time.min)
    end_of_day = datetime.datetime.combine(target_date, datetime.time.max)
    reservations_for_day = Reservation.query.filter(
        Reservation.start_time >= start_of_day,
        Reservation.start_time <= end_of_day
    ).all()
    
    timetable = {}
    for time_slot in time_slots:
        row = {}
        time_as_dt = datetime.datetime.strptime(time_slot, '%H:%M').time()
        for room in rooms:
            cell_data = None
            for res in reservations_for_day:
                if res.room_name == room and res.start_time.time() <= time_as_dt < res.end_time.time():
                    timeline_start_minutes = 9 * 60
                    reservation_start_minutes = res.start_time.hour * 60 + res.start_time.minute
                    reservation_end_minutes = res.end_time.hour * 60 + res.end_time.minute
                    duration_minutes = reservation_end_minutes - reservation_start_minutes
                    top_pixel = reservation_start_minutes - timeline_start_minutes
                    height_pixel = duration_minutes
                    cell_data = {
                        "user": res.booker.username, "purpose": res.purpose, "id": res.id,
                        "top": top_pixel, "height": height_pixel - 2,
                        "is_first_block": res.start_time.time() == time_as_dt,
                        "user_id": res.user_id
                    }
                    break
            row[room] = cell_data
        timetable[time_slot] = row
    
    prev_date = (target_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (target_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    return render_template('index.html', target_date_str=target_date.strftime('%Y-%m-%d'),
        timetable=timetable, time_slots=time_slots, rooms=rooms,
        prev_date=prev_date, next_date=next_date, show_prev_link=show_prev_link)

@app.route('/reserve', methods=['POST'])
@login_required
def reserve():
    room_name = request.form['room_name']
    purpose = request.form['purpose']
    date_str = request.form['date']
    start_time_str = request.form['start_time']
    end_time_str = request.form['end_time']
    repeat_type = request.form.get('repeat_type', 'none')
    repeat_count = int(request.form.get('repeat_count', 0))

    start_dt = datetime.datetime.strptime(f"{date_str} {start_time_str}", '%Y-%m-%d %H:%M')
    end_dt = datetime.datetime.strptime(f"{date_str} {end_time_str}", '%Y-%m-%d %H:%M')
    
    reservations_to_add = [{"start": start_dt, "end": end_dt}]
    if repeat_type != 'none' and repeat_count > 0:
        for _ in range(repeat_count):
            start_dt = start_dt + (datetime.timedelta(weeks=1) if repeat_type == 'weekly' else relativedelta(months=1))
            end_dt = end_dt + (datetime.timedelta(weeks=1) if repeat_type == 'weekly' else relativedelta(months=1))
            reservations_to_add.append({"start": start_dt, "end": end_dt})
            
    created_count, skipped_count = 0, 0
    for res_time in reservations_to_add:
        overlap = Reservation.query.filter(
            Reservation.room_name == room_name,
            Reservation.start_time < res_time['end'],
            Reservation.end_time > res_time['start']
        ).first()
        
        if not overlap:
            new_reservation = Reservation(
                purpose=purpose, room_name=room_name,
                start_time=res_time['start'], end_time=res_time['end'],
                user_id=current_user.id
            )
            db.session.add(new_reservation)
            created_count += 1
        else:
            skipped_count += 1

    db.session.commit()
    
    message = f"{created_count}件の予約を作成しました。"
    if skipped_count > 0:
        message += f" (重複のため {skipped_count}件はスキップされました)"
    flash(message, 'success')
        
    return redirect(url_for('index', date_str=date_str))

@app.route('/edit/<reservation_id>', methods=['GET', 'POST'])
@login_required
def edit_reservation(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        flash('エラー: 該当の予約を編集する権限がありません。', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        room_name = request.form['room_name']
        purpose = request.form['purpose']
        date_str = request.form['date']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        start_datetime = datetime.datetime.strptime(f"{date_str} {start_time_str}", '%Y-%m-%d %H:%M')
        end_datetime = datetime.datetime.strptime(f"{date_str} {end_time_str}", '%Y-%m-%d %H:%M')
        
        overlap = Reservation.query.filter(
            Reservation.id != reservation_id,
            Reservation.room_name == room_name,
            Reservation.start_time < end_datetime,
            Reservation.end_time > start_datetime
        ).first()

        if overlap:
            flash('エラー: その時間帯は既に他の予約と重複しています。', 'error')
            return render_template('edit.html', reservation=reservation, rooms=["会議室A", "会議室B", "会議室C", "大部屋"])
        else:
            reservation.purpose = purpose
            reservation.room_name = room_name
            reservation.start_time = start_datetime
            reservation.end_time = end_datetime
            db.session.commit()
            flash('予約を更新しました。', 'success')
            return redirect(url_for('index', date_str=date_str))
            
    return render_template('edit.html', reservation=reservation, rooms=["会議室A", "会議室B", "会議室C", "大部屋"])

@app.route('/cancel/<reservation_id>', methods=['POST'])
@login_required
def cancel(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if reservation and reservation.user_id == current_user.id:
        date_str = reservation.start_time.strftime('%Y-%m-%d')
        db.session.delete(reservation)
        db.session.commit()
        flash('予約をキャンセルしました。', 'success')
        return redirect(url_for('index', date_str=date_str))
    
    flash('エラー: 該当の予約をキャンセルする権限がありません。', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)