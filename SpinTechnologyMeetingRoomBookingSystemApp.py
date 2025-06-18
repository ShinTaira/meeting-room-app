# SpinTechnologyMeetingRoomBookingSystemApp.py (完成版)

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from dateutil.relativedelta import relativedelta
import datetime
import json
import uuid
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "reservations.json")
USERS_JSON_FILE_PATH = os.path.join(BASE_DIR, "users.json")

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.username = user_data.get('username')
        self.password_hash = user_data.get('password_hash')

    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

class ReservationSystem:
    def __init__(self, reservation_file=JSON_FILE_PATH, user_file=USERS_JSON_FILE_PATH):
        self.rooms = ["会議室A", "会議室B", "会議室C", "大部屋"]
        self.reservation_file = reservation_file
        self.user_file = user_file
        self.reservations = self.load_reservations()
        self.users = self.load_users()

    def make_reservation(self, user_name, purpose, room_name, start_time, end_time, user_id,
                         repeat_type='none', repeat_count=0):
        try:
            start_dt = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M')
            end_dt = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M')
            repeat_count = int(repeat_count)
        except (ValueError, TypeError):
            return {"success": False, "message": "日時の形式が正しくありません。"}

        reservations_to_add = []
        reservations_to_add.append({
            "id": str(uuid.uuid4()), "user_name": user_name, "purpose": purpose, 
            "room_name": room_name, "start_time": start_dt, "end_time": end_dt, "user_id": user_id
        })

        if repeat_type != 'none' and repeat_count > 0:
            current_start_dt, current_end_dt = start_dt, end_dt
            for _ in range(repeat_count):
                if repeat_type == 'weekly':
                    current_start_dt += datetime.timedelta(weeks=1)
                    current_end_dt += datetime.timedelta(weeks=1)
                elif repeat_type == 'monthly':
                    current_start_dt += relativedelta(months=1)
                    current_end_dt += relativedelta(months=1)
                
                reservations_to_add.append({
                    "id": str(uuid.uuid4()), "user_name": user_name, "purpose": purpose,
                    "room_name": room_name, "start_time": current_start_dt, "end_time": current_end_dt, "user_id": user_id
                })
        
        created_count, skipped_count = 0, 0
        for new_res in reservations_to_add:
            if not self.check_overlap(new_res['room_name'], new_res['start_time'], new_res['end_time']):
                self.reservations.append(new_res)
                created_count += 1
            else:
                skipped_count += 1
        
        if created_count > 0:
            self.save_reservations()
        
        return {"success": True, "created": created_count, "skipped": skipped_count}

    def cancel_reservation(self, reservation_id):
        initial_len = len(self.reservations)
        self.reservations = [r for r in self.reservations if r['id'] != reservation_id]
        if len(self.reservations) < initial_len:
            self.save_reservations()
            return True
        return False

    def check_overlap(self, room_name, start_time, end_time, existing_reservation_id=None):
        for r in self.reservations:
            if r['id'] == existing_reservation_id:
                continue
            if r['room_name'] == room_name:
                if start_time < r['end_time'] and r['start_time'] < end_time:
                    return True
        return False

    def find_reservation_by_id(self, reservation_id):
        return next((r for r in self.reservations if r['id'] == reservation_id), None)

    def update_reservation(self, reservation_id, user_name, purpose, room_name, start_time, end_time, user_id):
        reservation = self.find_reservation_by_id(reservation_id)
        if reservation:
            reservation.update({
                'user_name': user_name, 'purpose': purpose, 'room_name': room_name,
                'start_time': start_time, 'end_time': end_time, 'user_id': user_id
            })
            self.save_reservations()
            return True
        return False
    
    def load_reservations(self):
        try:
            with open(self.reservation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                item['start_time'] = datetime.datetime.fromisoformat(item['start_time'])
                item['end_time'] = datetime.datetime.fromisoformat(item['end_time'])
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_reservations(self):
        with open(self.reservation_file, 'w', encoding='utf-8') as f:
            json.dump(self.reservations, f, cls=DateTimeEncoder, indent=4, ensure_ascii=False)

    def load_users(self):
        try:
            with open(self.user_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_users(self):
        with open(self.user_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=4, ensure_ascii=False)

    def find_user_by_username(self, username):
        return next((u for u in self.users if u['username'] == username), None)

    def find_user_by_id(self, user_id):
        return next((u for u in self.users if u['id'] == user_id), None)

    def add_user(self, username, password):
        if self.find_user_by_username(username):
            return None
        new_user = {
            "id": str(uuid.uuid4()), "username": username,
            "password_hash": generate_password_hash(password)
        }
        self.users.append(new_user)
        self.save_users()
        return new_user  

# --- ここからシステムの実行デモ ---
if __name__ == "__main__":
    
    # 1. システムの準備
    system = ReservationSystem()
    
    # ★ここから祝日を取り込むデモを追加
    # =================================================================
    # ★ここに、ご自身で取得したAPIキーの文字列を貼り付けてください
    # =================================================================
    MY_API_KEY = "AIzaSyCTaK9UFVEMpucy-1cSRpoxLuYXGGRHL0c"

    if MY_API_KEY == "AIzaSyCTaK9UFVEMpucy-1cSRpoxLuYXGGRHL0c":
        print("【注意】APIキーが設定されていません。祝日の取り込みをスキップします。")
    else:
        # 来月(2025年7月)の祝日を取り込んでみましょう
        system.import_holidays_as_reservations(api_key=MY_API_KEY, year=2025, month=7)

    # 2. 今日の予約状況を表示
    TODAY = datetime.date.today().strftime("%Y-%m-%d")
    print("\n【会議室予約システム デモ】\n")
    print("--- STEP1: 今日の予約状況の表示 ---")
    for room in system.rooms:
        system.show_reservations(room, TODAY)

    # 3. 来月の祝日（海の日: 7/21）が登録されているか確認
    print("\n--- STEP2: 来月の祝日の予約状況を確認 ---")
    system.show_reservations("会議室A", "2025-07-21")