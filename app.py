# app.py (予約キャンセル機能付き)

from flask import Flask, render_template, request, redirect, url_for
from SpinTechnologyMeetingRoomBookingSystemApp import ReservationSystem
import datetime

app = Flask(__name__)
system = ReservationSystem()

@app.route('/')
@app.route('/<date_str>')
def index(date_str=None):
    if date_str is None:
        target_date = datetime.date.today()
    else:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = datetime.date.today()

    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 24) for m in (0, 30)]
    reservations_for_day = [r for r in system.reservations if r['start_time'].date() == target_date]

    timetable = {}
    for time_slot in time_slots:
        row = {}
        time_as_dt = datetime.datetime.strptime(time_slot, '%H:%M').time()
        for room in system.rooms:
            # ★修正: デフォルトはNone(空)にする
            cell_data = None 
            for res in reservations_for_day:
                if res['room_name'] == room and res['start_time'].time() <= time_as_dt < res['end_time'].time():
                    # ★修正: 予約IDも格納する
                    cell_data = {
                        "user": res['user_name'],
                        "purpose": res['purpose'],
                        "id": res['id']
                    }
                    # 予約の開始時刻の場合のみセルに表示
                    if res['start_time'].time() != time_as_dt:
                        cell_data = " " # 予約の2枠目以降は空白
                    break
            row[room] = cell_data
        timetable[time_slot] = row
    
    prev_date = (target_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (target_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template(
        'index.html',
        target_date_str=target_date.strftime('%Y-%m-%d'),
        timetable=timetable,
        time_slots=time_slots,
        rooms=system.rooms
    )

@app.route('/reserve', methods=['POST'])
def reserve():
    room_name = request.form['room_name']
    user_name = request.form['user_name']
    purpose = request.form['purpose']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    
    start_datetime_str = f"{date} {start_time}"
    end_datetime_str = f"{date} {end_time}"
    
    system.make_reservation(
        user_name=user_name, purpose=purpose, room_name=room_name,
        start_time=start_datetime_str, end_time=end_datetime_str
    )
    
    return redirect(url_for('index', date_str=date))

# ★ここから新しい関数を追加
@app.route('/cancel/<reservation_id>', methods=['POST'])
def cancel(reservation_id):
    """予約をキャンセルする"""
    # キャンセルする前に、どの日のページに戻るか日付を取得しておく
    target_reservation = next((r for r in system.reservations if r['id'] == reservation_id), None)
    if target_reservation:
        date_str = target_reservation['start_time'].strftime('%Y-%m-%d')
        system.cancel_reservation(reservation_id)
        return redirect(url_for('index', date_str=date_str))
    
    # 予約が見つからなかった場合はトップページへ
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
