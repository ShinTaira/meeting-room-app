import datetime
import json
import uuid
import os
from googleapiclient.discovery import build
from calendar import monthrange

# --- ファイルパスとエンコーダーの定義 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "reservations.json")

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

# --- 予約システム本体 ---
class ReservationSystem:
    def __init__(self, filename=JSON_FILE_PATH):
        self.rooms = ["会議室A", "会議室B", "会議室C", "大部屋"]
        self.filename = filename
        self.reservations = self.load_from_file()

    def load_from_file(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                reservations_data = json.load(f)
                return [{**r, 'start_time': datetime.datetime.fromisoformat(r['start_time']), 'end_time': datetime.datetime.fromisoformat(r['end_time'])} for r in reservations_data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_to_file(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.reservations, f, cls=DateTimeEncoder, indent=4, ensure_ascii=False)

    def make_reservation(self, user_name, purpose, room_name, start_time, end_time):
        try:
            start = datetime.datetime.fromisoformat(start_time)
            end = datetime.datetime.fromisoformat(end_time)
        except ValueError:
            print(f"エラー: 時刻は 'YYYY-MM-DD HH:MM' の形式で入力してください。")
            return False
        if start >= end:
            print("エラー: 終了時刻は開始時刻より後に設定してください。")
            return False
        if room_name not in self.rooms:
            print(f"エラー: 会議室 '{room_name}' は存在しません。")
            return False
        if not (datetime.time(9, 0) <= start.time() and end.time() <= datetime.time(23, 30)):
            print("エラー: 予約時間は 9:00 から 23:30 の間でなければなりません。")
            return False
        if start.minute not in [0, 30] or end.minute not in [0, 30]:
            print("エラー: 予約時間は30分単位で指定してください。")
            return False
        for r in self.reservations:
            if r['room_name'] == room_name and start < r['end_time'] and end > r['start_time']:
                print(f"エラー: その時間帯は既に予約されています。（予約者: {r['user_name']}さん）")
                return False
        new_reservation = {'id': str(uuid.uuid4()), 'user_name': user_name, 'purpose': purpose, 'room_name': room_name, 'start_time': start, 'end_time': end}
        self.reservations.append(new_reservation)
        self.save_to_file()
        print(f"予約完了: {room_name} | {start.strftime('%Y-%m-%d %H:%M')}-{end.strftime('%H:%M')} | {user_name}さん (目的: {purpose})")
        return True

    def show_reservations(self, room_name, date_str):
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print(f"エラー: 日付は 'YYYY-MM-DD' の形式で入力してください。")
            return
        print(f"\n--- {room_name} の予約状況 ({date_str}) ---")
        room_reservations = sorted([r for r in self.reservations if r['room_name'] == room_name and r['start_time'].date() == target_date], key=lambda x: x['start_time'])
        if not room_reservations:
            print("この日の予約はありません。")
            return
        for r in room_reservations:
            print(f"・ {r['start_time'].strftime('%H:%M')} - {r['end_time'].strftime('%H:%M')} | {r['user_name']}さん (目的: {r['purpose']}) [ID: {r['id']}]")

    def cancel_reservation(self, reservation_id):
        target_reservation = next((r for r in self.reservations if r['id'] == reservation_id), None)
        if not target_reservation:
            print(f"エラー: ID '{reservation_id}' の予約が見つかりません。")
            return False
        self.reservations.remove(target_reservation)
        self.save_to_file()
        print(f"キャンセル完了: {target_reservation['room_name']} の {target_reservation['user_name']}さんの予約を削除しました。")
        return True

    def import_holidays_as_reservations(self, api_key, year, month):
        print(f"\n--- {year}年{month}月の祝日をGoogleカレンダーから取得します ---")
        try:
            service = build('calendar', 'v3', developerKey=api_key)
            start_of_month = datetime.datetime(year, month, 1)
            end_of_month_day = monthrange(year, month)[1]
            end_of_month = datetime.datetime(year, month, end_of_month_day, 23, 59, 59)
            events_result = service.events().list(calendarId='ja.japanese#holiday@group.v.calendar.google.com', timeMin=start_of_month.isoformat()+'Z', timeMax=end_of_month.isoformat()+'Z', singleEvents=True, orderBy='startTime').execute()
            holidays = events_result.get('items', [])
            if not holidays:
                print("祝日は見つかりませんでした。")
                return
            imported_count = 0
            for holiday in holidays:
                holiday_name = holiday['summary']
                date_str = holiday['start'].get('date')
                for room in self.rooms:
                    is_already = any(r['purpose'] == holiday_name and r['room_name'] == room and r['start_time'].date().isoformat() == date_str for r in self.reservations)
                    if not is_already:
                        print(f"  > {date_str} ({holiday_name}) を {room} の予約として追加します。")
                        self.make_reservation("祝日", holiday_name, room, f"{date_str} 09:00", f"{date_str} 23:30")
                        imported_count += 1
            if imported_count > 0:
                print(f"--- {imported_count}件の祝日予約を取り込みました ---")
            else:
                print("--- 新しく取り込む祝日はありませんでした ---")
        except Exception as e:
            print(f"エラー: Googleカレンダーからの祝日取得に失敗しました。 > {e}")
            print("  > APIキーが正しいか、Google Calendar APIが有効になっているか確認してください。")

# --- ここからシステムの実行デモ ---
if __name__ == "__main__":
    system = ReservationSystem()

    # ★修正: コードに直接書く代わりに、環境変数からAPIキーを読み込む
    # os.environ.get('GOOGLE_API_KEY') は「GOOGLE_API_KEYという名前の環境変数をください」という意味
    MY_API_KEY = os.environ.get('GOOGLE_API_KEY')

    # MY_API_KEYが設定されていない場合（ローカルPCでテストする時など）
    if not MY_API_KEY:
        print("【注意】APIキーが環境変数に設定されていません。祝日の取り込みをスキップします。")
    else:
        # 今月の祝日を取り込むように変更
        today = datetime.date.today()
        system.import_holidays_as_reservations(api_key=MY_API_KEY, year=today.year, month=today.month)