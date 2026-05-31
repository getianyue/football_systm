from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from qfluentwidgets import TitleLabel


class SystemPage(QWidget):

    def __init__(self):
        super().__init__()
        self.setObjectName("system_page")
        layout = QVBoxLayout(self)

        title = TitleLabel("系统信息")

        info = QLabel(
            "开发工具：Python + PySide6\n\n"
            "目标检测：YOLO\n\n"
            "目标跟踪：DeepSORT\n\n"
            "数据库：MySQL\n\n"
            "GUI框架：PySide6-Fluent-Widgets"
        )

        layout.addWidget(title)
        layout.addWidget(info)