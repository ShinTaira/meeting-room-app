# app.py (Googleカレンダー風デザイン対応版)

from flask import Flask, render_template, request, redirect, url_for
from SpinTechnologyMeetingRoomBookingSystemApp import ReservationSystem
import datetime

app = Flask(__name__)
system = ReservationSystem()

@app.route('/')
@app.route('/<date_str>')
def index(date_str=None):
    if date_str is None:
        # ★修正: 日付指定がない場合は、必ず今日の日付にリダイレクトする
        return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))
    
    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # ★修正: 不正な日付形式の場合も今日にリダイレクト
        return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))

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
                    # ★修正: 予約の長さ(分)と、何番目のブロックかの情報を追加
                    duration_minutes = (res['end_time'] - res['start_time']).total_seconds() / 60
                    time_diff_minutes = ((datetime.datetime.combine(datetime.date.min, time_as_dt) - 
                                          datetime.datetime.combine(datetime.date.min, res['start_time'].time())).total_seconds() / 60)
                    
                    cell_data = {
                        "user": res['user_name'], "purpose": res['purpose'], "id": res['id'],
                        "duration": duration_minutes,
                        "is_first_block": res['start_time'].time() == time_as_dt,
                    }
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
        rooms=system.rooms,
        prev_date=prev_date,
        next_date=next_date
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

@app.route('/cancel/<reservation_id>', methods=['POST'])
def cancel(reservation_id):
    target_reservation = next((r for r in system.reservations if r['id'] == reservation_id), None)
    if target_reservation:
        date_str = target_reservation['start_time'].strftime('%Y-%m-%d')
        system.cancel_reservation(reservation_id)
        return redirect(url_for('index', date_str=date_str))
    
    return redirect(url_for('index', date_str=datetime.date.today().strftime('%Y-%m-%d')))


if __name__ == '__main__':
    app.run(debug=True)
