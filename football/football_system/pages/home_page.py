from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, StrongBodyLabel, SubtitleLabel, TitleLabel

from db.mysql_helper import MysqlHelper


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("home_page")
        self.stat_labels = {}
        self.status_label = None
        self.empty_label = None
        self.init_ui()
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        title = TitleLabel("足球运动目标分析系统")
        subtitle = SubtitleLabel("Football Motion Analysis and Tracking System")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        stats_layout.addWidget(self.create_stat_card("平均速度", "avg_speed", "video_results 表统计结果"))
        stats_layout.addWidget(self.create_stat_card("平均加速度", "avg_acc", "video_results 表统计结果"))
        stats_layout.addWidget(self.create_stat_card("分析视频数", "video_count", "历史分析记录数量"))
        stats_layout.addWidget(self.create_stat_card("系统状态", "system_status", "数据库连接和界面运行状态"))
        main_layout.addLayout(stats_layout)

        self.empty_label = QLabel("暂无分析结果，请上传视频开始分析")
        self.empty_label.setStyleSheet("color: #666; font-size: 16px;")
        main_layout.addWidget(self.empty_label)

        center_layout = QHBoxLayout()
        center_layout.setSpacing(20)

        intro_card = CardWidget()
        intro_layout = QVBoxLayout(intro_card)
        intro_layout.addWidget(StrongBodyLabel("系统介绍"))
        intro_text = QLabel(
            "本系统基于 YOLO 与 DeepSORT 实现足球运动目标检测与跟踪，"
            "结合单应矩阵完成像素坐标到场地坐标的映射，统计 Track ID 的平均速度、"
            "平均加速度，并将分析结果保存到 MySQL。"
        )
        intro_text.setWordWrap(True)
        intro_layout.addWidget(intro_text)
        intro_layout.addStretch()

        status_card = CardWidget()
        status_layout = QVBoxLayout(status_card)
        status_layout.addWidget(StrongBodyLabel("模块状态"))
        status_layout.addWidget(self.create_status_item("YOLO 检测模型", "可用"))
        status_layout.addWidget(self.create_status_item("DeepSORT 跟踪", "可用"))
        status_layout.addWidget(self.create_status_item("MySQL 数据库", "system_status"))
        status_layout.addStretch()

        center_layout.addWidget(intro_card, 2)
        center_layout.addWidget(status_card, 1)
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

    def refresh(self):
        summary = self._load_summary()
        video_count = summary["video_count"]
        values = {
            "avg_speed": f"{summary['avg_speed']:.2f} m/s" if video_count else "--",
            "avg_acc": f"{summary['avg_acc']:.2f} m/s^2" if video_count else "--",
            "video_count": str(video_count),
            "system_status": summary["system_status"],
        }

        for key, label in self.stat_labels.items():
            label.setText(values[key])

        if self.status_label:
            self.status_label.setText(summary["system_status"])
            color = "green" if summary["system_status"] == "Online" else "red"
            self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        self.empty_label.setVisible(video_count == 0)

    def _load_summary(self):
        try:
            return MysqlHelper.get_summary()
        except Exception:
            return {
                "video_count": 0,
                "avg_speed": 0.0,
                "avg_acc": 0.0,
                "system_status": "Database Offline",
            }

    def create_stat_card(self, title_text, key, desc_text):
        card = CardWidget()
        card.setMinimumHeight(150)
        layout = QVBoxLayout(card)
        title = StrongBodyLabel(title_text)
        value = TitleLabel("--")
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        self.stat_labels[key] = value

        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(value)
        layout.addStretch()
        layout.addWidget(desc)
        return card

    def create_status_item(self, name, status):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        name_label = QLabel(name)
        status_label = QLabel("Online" if status != "system_status" else "--")
        status_label.setStyleSheet("color: green; font-weight: bold;")
        if status == "system_status":
            self.status_label = status_label

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(status_label)
        return frame
