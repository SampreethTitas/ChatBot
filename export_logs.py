from models import db, ChatLog, User
import csv

def export_chat_logs(file_name="chat_logs.csv"):
    logs = ChatLog.query.all()
    with open(file_name, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Username", "User Message", "Bot Response", "Timestamp"])
        for log in logs:
            writer.writerow([log.user.username, log.user_message, log.bot_response, log.timestamp])