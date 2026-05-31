from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, TitleLabel

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from db.mysql_helper import MysqlHelper


class DataPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("data_page")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = TitleLabel("Track 运动数据分析")
        self.empty_label = QLabel("暂无分析结果，请上传视频开始分析")
        self.empty_label.setStyleSheet("color: #666; font-size: 15px;")

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["视频名称", "Track ID", "平均速度(m/s)", "平均加速度(m/s^2)"])

        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout.addWidget(title)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table)
        layout.addWidget(self.canvas)

        self.refresh()

    def refresh(self):
        self.load_data()

    def load_data(self):
        try:
            rows = MysqlHelper.get_player_data()
        except Exception as exc:
            rows = []
            InfoBar.error(
                title="数据库错误",
                content=str(exc),
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

        self.empty_label.setVisible(len(rows) == 0)
        self.table.setRowCount(len(rows))
        track_labels = []
        speeds = []

        for row_idx, row in enumerate(rows):
            video_name, track_id, avg_speed, avg_acc = row
            values = [video_name, f"Track ID {track_id}", f"{float(avg_speed):.2f}", f"{float(avg_acc):.2f}"]
            for col_idx, value in enumerate(values):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
            track_labels.append(f"Track ID {track_id}")
            speeds.append(float(avg_speed))

        self.table.resizeColumnsToContents()
        self.draw_speed_chart(track_labels, speeds)

    def draw_speed_chart(self, labels, speeds):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if labels:
            ax.bar(labels, speeds, color="#3b82f6")
            ax.set_title("Track Average Speed")
            ax.set_xlabel("Track ID")
            ax.set_ylabel("Average Speed (m/s)")
            ax.tick_params(axis="x", rotation=30)
        else:
            ax.text(0.5, 0.5, "暂无 Track 数据", ha="center", va="center")
            ax.set_axis_off()

        self.figure.tight_layout()
        self.canvas.draw()
