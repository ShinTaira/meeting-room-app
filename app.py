# app.py (全面的なアップデート版)

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from SpinTechnologyMeetingRoomBookingSystemApp import ReservationSystem, User
import datetime

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here' # 以前設定したものと同じでOK

# --- Flask-Loginの設定 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # 未ログイン時にリダイレクトする先
login_manager.login_message = "このページにアクセスするにはログインが必要です。"

system = ReservationSystem()

@login_manager.user_loader
def load_user(user_id):
    user_data = system.find_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

# --- 認証ルート ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = system.find_user_by_username(username)
        if user_data and User.check_password(user_data['password_hash'], password):
            user = User(user_data)
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
        if system.find_user_by_username(username):
            flash('そのユーザー名は既に使用されています。', 'error')
        else:
            system.add_user(username, password)
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- メインの予約システムルート (要ログイン) ---
@app.route('/')
@app.route('/<date_str>')
@login_required
def index(date_str=None):
    # (この関数の中身は以前のものと同じでOK。app.pyをまるごと置き換えてください)
    if date_str is None:
        return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))
    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))
    limit_date = datetime.date.today() - datetime.timedelta(days=30)
    show_prev_link = target_date > limit_date
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 24) for m in (0, 30)]
    reservations_for_day = [r for r in system.reservations if r['start_time'].date() == target_date]
    timetable = {}
    for time_slot in time_slots:
        row = {}
        time_as_dt = datetime.datetime.strptime(time_slot, '%H:%M').time()
        for room in system.rooms:
            cell_data = None
            for res in reservations_for_day:
                if res['room_name'] == room and res['start_time'].time() <= time_as_dt < res['end_time'].time():
                    timeline_start_minutes = 9 * 60
                    reservation_start_minutes = res['start_time'].hour * 60 + res['start_time'].minute
                    reservation_end_minutes = res['end_time'].hour * 60 + res['end_time'].minute
                    duration_minutes = reservation_end_minutes - reservation_start_minutes
                    top_pixel = reservation_start_minutes - timeline_start_minutes
                    height_pixel = duration_minutes
                    cell_data = {
                        "user": res['user_name'], "purpose": res['purpose'], "id": res['id'],
                        "top": top_pixel, "height": height_pixel - 2,
                        "is_first_block": res['start_time'].time() == time_as_dt,
                        "user_id": res.get('user_id') # .get()を使うことで、キーがなくてもエラーにならない
                    }
                    break
            row[room] = cell_data
        timetable[time_slot] = row
    prev_date = (target_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (target_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    return render_template(
        'index.html', target_date_str=target_date.strftime('%Y-%m-%d'),
        timetable=timetable, time_slots=time_slots, rooms=system.rooms,
        prev_date=prev_date, next_date=next_date, show_prev_link=show_prev_link
    )

@app.route('/reserve', methods=['POST'])
@login_required
def reserve():
    # ... (前回のステップ4で修正した内容と同じでOK。app.pyをまるごと置き換えてください)
    room_name = request.form['room_name']
    user_name = current_user.username # ★予約者名をログインユーザー名に
    purpose = request.form['purpose']
    date = request.form['date']
    start_time_str = request.form['start_time']
    end_time_str = request.form['end_time']
    repeat_type = request.form.get('repeat_type', 'none')
    repeat_count = request.form.get('repeat_count', 0)
    start_datetime_str = f"{date} {start_time_str}"
    end_datetime_str = f"{date} {end_time_str}"
    
    # ★予約処理に user_id を追加
    result = system.make_reservation(
        user_name=user_name, purpose=purpose, room_name=room_name,
        start_time=start_datetime_str, end_time=end_datetime_str,
        repeat_type=repeat_type, repeat_count=repeat_count,
        user_id=current_user.id # ★user_idを渡す
    )
    if result.get('success'):
        message = f"{result.get('created', 0)}件の予約を作成しました。"
        if result.get('skipped', 0) > 0:
            message += f" (重複のため {result.get('skipped')}件はスキップされました)"
        flash(message, 'success')
    else:
        flash(f"エラー: {result.get('message', '不明なエラー')}", 'error')
    return redirect(url_for('index', date_str=date))


@app.route('/edit/<reservation_id>', methods=['GET', 'POST'])
@login_required
def edit_reservation(reservation_id):
    reservation = system.find_reservation_by_id(reservation_id)
    # ★本人確認
    if not reservation or reservation.get('user_id') != current_user.id:
        flash('エラー: 該当の予約を編集する権限がありません。', 'error')
        return redirect(url_for('index'))
    
    # (この関数の中身はステップ2のものとほぼ同じ。app.pyをまるごと置き換えてください)
    if request.method == 'POST':
        room_name = request.form['room_name']
        purpose = request.form['purpose']
        date = request.form['date']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        start_datetime = datetime.datetime.strptime(f"{date} {start_time_str}", '%Y-%m-%d %H:%M')
        end_datetime = datetime.datetime.strptime(f"{date} {end_time_str}", '%Y-%m-%d %H:%M')
        if system.check_overlap(room_name, start_datetime, end_datetime, existing_reservation_id=reservation_id):
            flash('エラー: その時間帯は既に他の予約と重複しています。', 'error')
            return render_template('edit.html', reservation=reservation, rooms=system.rooms)
        else:
            # ★更新処理に user_id を追加
            system.update_reservation(
                reservation_id, current_user.username, purpose, room_name, start_datetime, end_datetime, current_user.id
            )
            flash('予約を更新しました。', 'success')
            return redirect(url_for('index', date_str=date))
    return render_template('edit.html', reservation=reservation, rooms=system.rooms)

@app.route('/cancel/<reservation_id>', methods=['POST'])
@login_required
def cancel(reservation_id):
    target_reservation = system.find_reservation_by_id(reservation_id)
    # ★本人確認
    if target_reservation and target_reservation.get('user_id') == current_user.id:
        date_str = target_reservation['start_time'].strftime('%Y-%m-%d')
        system.cancel_reservation(reservation_id)
        flash('予約をキャンセルしました。', 'success')
        return redirect(url_for('index', date_str=date_str))
    
    flash('エラー: 該当の予約をキャンセルする権限がありません。', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)