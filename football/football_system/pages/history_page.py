from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, TitleLabel

from db.mysql_helper import MysqlHelper


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("history_page")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = TitleLabel("历史分析记录")
        self.empty_label = QLabel("暂无分析结果，请上传视频开始分析")
        self.empty_label.setStyleSheet("color: #666; font-size: 15px;")

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["视频名称", "平均速度(m/s)", "平均加速度(m/s^2)", "Track 数量", "分析时间"]
        )

        layout.addWidget(title)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        self.load_data()

    def load_data(self):
        try:
            rows = MysqlHelper.get_history()
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

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                text = f"{value:.2f}" if isinstance(value, float) else str(value)
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(text))

        self.table.resizeColumnsToContents()
