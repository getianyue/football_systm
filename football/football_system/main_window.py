from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow

try:
    from .pages.data_page import DataPage
    from .pages.history_page import HistoryPage
    from .pages.home_page import HomePage
    from .pages.system_page import SystemPage
    from .pages.video_page import VideoPage
except ImportError:
    from pages.data_page import DataPage
    from pages.history_page import HistoryPage
    from pages.home_page import HomePage
    from pages.system_page import SystemPage
    from pages.video_page import VideoPage


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Football Motion Analysis System")
        self.resize(1400, 900)
        self.init_pages()
        self.init_navigation()

    def init_pages(self):
        self.home_page = HomePage()
        self.video_page = VideoPage()
        self.data_page = DataPage()
        self.history_page = HistoryPage()
        self.system_page = SystemPage()
        self.video_page.resultsChanged.connect(self.refresh_result_pages)

    def init_navigation(self):
        self.addSubInterface(self.home_page, FIF.HOME, "首页")
        self.addSubInterface(self.video_page, FIF.VIDEO, "视频分析")
        self.addSubInterface(self.data_page, FIF.PIE_SINGLE, "数据分析")
        self.addSubInterface(self.history_page, FIF.HISTORY, "历史记录")
        self.addSubInterface(self.system_page, FIF.SETTING, "系统信息")

    def refresh_result_pages(self):
        self.home_page.refresh()
        self.history_page.refresh()
        self.data_page.refresh()
