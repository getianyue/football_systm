from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, LineEdit, PasswordLineEdit, PushButton, SubtitleLabel, TitleLabel

try:
    from .main_window import MainWindow
except ImportError:
    from main_window import MainWindow


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Football Motion Analysis System")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(80, 40, 80, 40)

        title = TitleLabel("Football Motion Analysis System")
        subtitle = SubtitleLabel("足球运动目标分析系统")

        self.username = LineEdit()
        self.username.setPlaceholderText("请输入用户名")

        self.password = PasswordLineEdit()
        self.password.setPlaceholderText("请输入密码")

        login_btn = PushButton("登录")
        login_btn.clicked.connect(self.login)

        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(login_btn)

    def login(self):
        user = self.username.text()
        pwd = self.password.text()

        if user == "admin" and pwd == "123456":
            self.main_window = MainWindow()
            self.main_window.show()
            self.close()
            return

        InfoBar.error(
            title="登录失败",
            content="用户名或密码错误",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )
