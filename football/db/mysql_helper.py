import os
from datetime import datetime


class MysqlHelper:
    HOST = os.getenv("FOOTBALL_DB_HOST", "localhost")
    PORT = int(os.getenv("FOOTBALL_DB_PORT", "3306"))
    USER = os.getenv("FOOTBALL_DB_USER", "root")
    PASSWORD = os.getenv("FOOTBALL_DB_PASSWORD", "123456")
    DATABASE = os.getenv("FOOTBALL_DB_NAME", "football_system")

    @classmethod
    def get_conn(cls):
        import pymysql

        return pymysql.connect(
            host=cls.HOST,
            port=cls.PORT,
            user=cls.USER,
            password=cls.PASSWORD,
            database=cls.DATABASE,
            charset="utf8mb4",
            autocommit=False,
        )

    @classmethod
    def ensure_tables(cls):
        conn = cls.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS video_results (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        video_name VARCHAR(255),
                        avg_speed FLOAT,
                        avg_acc FLOAT,
                        track_count INT,
                        analysis_time DATETIME
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS player_results (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        video_name VARCHAR(255),
                        track_id INT,
                        avg_speed FLOAT,
                        avg_acc FLOAT
                    )
                    """
                )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def insert_analysis_result(cls, video_result, avg_speeds, avg_accs):
        cls.ensure_tables()
        conn = cls.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO video_results
                        (video_name, avg_speed, avg_acc, track_count, analysis_time)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        video_result["video_name"],
                        float(video_result["avg_speed"]),
                        float(video_result["avg_acc"]),
                        int(video_result["track_count"]),
                        video_result.get("analysis_time") or datetime.now(),
                    ),
                )

                for track_id, avg_speed in avg_speeds.items():
                    cursor.execute(
                        """
                        INSERT INTO player_results
                            (video_name, track_id, avg_speed, avg_acc)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            video_result["video_name"],
                            int(track_id),
                            float(avg_speed),
                            float(avg_accs.get(track_id, 0.0)),
                        ),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def get_summary(cls):
        conn = cls.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS video_count,
                        COALESCE(AVG(avg_speed), 0) AS avg_speed,
                        COALESCE(AVG(avg_acc), 0) AS avg_acc
                    FROM video_results
                    """
                )
                row = cursor.fetchone()
                return {
                    "video_count": int(row[0] or 0),
                    "avg_speed": float(row[1] or 0),
                    "avg_acc": float(row[2] or 0),
                    "system_status": "Online",
                }
        finally:
            conn.close()

    @classmethod
    def get_history(cls):
        conn = cls.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT video_name, avg_speed, avg_acc, track_count, analysis_time
                    FROM video_results
                    ORDER BY analysis_time DESC, id DESC
                    """
                )
                return cursor.fetchall()
        finally:
            conn.close()

    @classmethod
    def get_player_data(cls):
        conn = cls.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT video_name, track_id, avg_speed, avg_acc
                    FROM player_results
                    ORDER BY video_name DESC, track_id ASC
                    """
                )
                return cursor.fetchall()
        finally:
            conn.close()

    @classmethod
    def clear_results(cls):
        cls.ensure_tables()
        conn = cls.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM player_results")
                cursor.execute("DELETE FROM video_results")
                cursor.execute("ALTER TABLE player_results AUTO_INCREMENT = 1")
                cursor.execute("ALTER TABLE video_results AUTO_INCREMENT = 1")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
