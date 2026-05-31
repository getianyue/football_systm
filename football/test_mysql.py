import pymysql
from datetime import datetime

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="123456",
    database="football_analysis"
)

cursor = conn.cursor()

sql = """
INSERT INTO analysis_results
(video_name, avg_speed,
 avg_acc, track_count, analysis_time)

VALUES (%s, %s, %s, %s, %s)
"""

data = (
    "match.mp4",
    5.2,
    1.4,
    12,
    datetime.now()
)

cursor.execute(sql, data)

conn.commit()

print("数据插入成功！")

conn.close()