import json
import sys
from pathlib import Path

import cv2
from PySide6.QtCore import QCoreApplication, QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, PushButton, StrongBodyLabel, TitleLabel

from api.reset import clear_results


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LATEST_RESULT_FILE = PROJECT_ROOT / "data" / "latest_result.json"
ANALYSIS_SCRIPT = PROJECT_ROOT / "analysis.py"


class VideoPage(QWidget):
    resultsChanged = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("video_page")
        self.video_path = None
        self.process = None
        self.cap = None
        self.current_pixmap = None
        self.current_result_video = None
        self._last_error_text = ""
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._next_video_frame)
        self.init_ui()
        self.reset_display()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setWordWrap(True)
        self.video_label.setMinimumSize(760, 480)
        self.video_label.setStyleSheet(
            """
            background-color: #202020;
            color: white;
            font-size: 18px;
            border-radius: 8px;
            """
        )

        right_panel = CardWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(14)

        title = TitleLabel("视频分析")
        result_title = StrongBodyLabel("当前结果")
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)

        self.open_btn = PushButton("导入视频")
        self.start_btn = PushButton("开始分析")
        self.reset_btn = PushButton("清空历史结果 / 重置演示数据")

        self.open_btn.clicked.connect(self.open_video)
        self.start_btn.clicked.connect(self.start_analysis)
        self.reset_btn.clicked.connect(self.reset_demo_data)

        right_layout.addWidget(title)
        right_layout.addWidget(result_title)
        right_layout.addWidget(self.info_label)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.open_btn)
        right_layout.addWidget(self.start_btn)
        right_layout.addWidget(self.reset_btn)
        right_layout.addStretch()

        main_layout.addWidget(self.video_label, 3)
        main_layout.addWidget(right_panel, 1)

    def reset_display(self):
        self.stop_playback()
        self.video_path = None
        self.current_pixmap = None
        self.current_result_video = None
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText("暂无分析结果，请上传视频开始分析")
        self.info_label.setText("当前状态：暂无分析结果\n\n请导入视频后点击“开始分析”。")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_pixmap:
            self._show_pixmap(self.current_pixmap)

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频",
            str(PROJECT_ROOT / "data"),
            "Video Files (*.mp4 *.avi *.mov)",
        )

        if not path:
            return

        self.stop_playback()
        self.video_path = path
        self.current_pixmap = None
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText("视频已导入，等待开始分析")
        self.info_label.setText(f"已加载视频：\n{path}\n\n点击“开始分析”重新执行检测、跟踪和可视化输出。")

    def start_analysis(self):
        if not self.video_path:
            QMessageBox.warning(self, "提示", "请先导入视频")
            return

        if self.process and self.process.state() != QProcess.NotRunning:
            QMessageBox.information(self, "提示", "视频正在分析，请等待当前任务完成")
            return

        self.stop_playback()
        self.process = QProcess(self)
        self._last_error_text = ""
        self.process.setWorkingDirectory(str(PROJECT_ROOT))
        self.process.setProgram(sys.executable)
        self.process.setArguments([str(ANALYSIS_SCRIPT), self.video_path])
        self.process.readyReadStandardError.connect(self._read_process_error)
        self.process.finished.connect(self._analysis_finished)
        self.process.errorOccurred.connect(self._analysis_error)

        self.start_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText("正在生成分析视频，请等待...")
        self.info_label.setText("正在分析，请等待...\n\n将生成带检测框、Track ID、速度、轨迹和右上角顶视图的结果视频。")
        self.process.start()

        if not self.process.waitForStarted(3000):
            self._set_buttons_enabled(True)
            QMessageBox.critical(self, "错误", "analysis.py 启动失败")

    def reset_demo_data(self):
        if self.process and self.process.state() != QProcess.NotRunning:
            QMessageBox.warning(self, "提示", "视频正在分析，分析结束后再清空历史结果。")
            return

        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空数据库历史记录和本地分析结果文件吗？\n不会删除测试视频、模型文件和源码。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.release_result_video()

        try:
            result = clear_results()
        except Exception as exc:
            QMessageBox.critical(self, "清空失败", str(exc))
            return

        self.video_path = None
        self.video_label.setText("历史结果已清空，请重新上传视频分析")
        self.info_label.setText("历史结果已清空\n\n请重新导入视频并点击“开始分析”。")
        self.resultsChanged.emit()
        message = result.get("message", "历史结果已清空")
        warnings = result.get("warnings") or []
        if warnings:
            message += "\n\n部分被占用文件已跳过，不影响重新演示。"
        QMessageBox.information(self, "完成", message)

    def release_result_video(self):
        self.stop_playback()
        self.current_result_video = None
        self.current_pixmap = None
        self.video_label.setPixmap(QPixmap())
        self.video_label.clear()
        QCoreApplication.processEvents()

    def play_result_video(self, video_path):
        self.stop_playback()
        video_path = Path(video_path)
        if not video_path.exists():
            QMessageBox.warning(self, "提示", f"结果视频不存在：{video_path}")
            return

        self.cap = cv2.VideoCapture(str(video_path))
        if not self.cap.isOpened():
            self.cap = None
            QMessageBox.warning(self, "提示", f"无法打开结果视频：{video_path}")
            return

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_result_video = str(video_path)
        interval = int(1000 / fps) if fps and fps > 1 else 40
        self._next_video_frame()
        self.play_timer.start(max(15, interval))

    def stop_playback(self):
        self.play_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()

    def _next_video_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                self.stop_playback()
                return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = frame_rgb.shape
        image = QImage(frame_rgb.data, width, height, channels * width, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image)
        self.current_pixmap = pixmap
        self._show_pixmap(pixmap)

    def _show_pixmap(self, pixmap):
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setText("")
        self.video_label.setPixmap(scaled)

    def _read_process_error(self):
        if not self.process:
            return
        error_text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="ignore").strip()
        if error_text:
            self._last_error_text = error_text

    def _analysis_error(self, error):
        self._set_buttons_enabled(True)
        QMessageBox.critical(self, "错误", f"分析进程异常：{error}")

    def _analysis_finished(self, exit_code, exit_status):
        self._set_buttons_enabled(True)

        if exit_code != 0:
            message = self._last_error_text or "analysis.py 执行失败"
            QMessageBox.critical(self, "分析失败", message)
            self.info_label.setText("分析失败，请查看错误提示。")
            return

        try:
            with LATEST_RESULT_FILE.open("r", encoding="utf-8") as f:
                result = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"读取 latest_result.json 失败：{exc}")
            self.info_label.setText("分析完成，但读取结果失败。")
            return

        avg_speed = float(result.get("avg_speed", 0))
        avg_acc = float(result.get("avg_acc", 0))
        track_count = int(result.get("track_count", 0))
        output_video = result.get("output_video")

        self.info_label.setText(
            "分析完成，正在播放结果视频\n\n"
            f"平均速度：{avg_speed:.2f} m/s\n"
            f"平均加速度：{avg_acc:.2f} m/s^2\n"
            f"Track 数量：{track_count}"
        )
        if output_video:
            self.play_result_video(output_video)

        self.resultsChanged.emit()
        QMessageBox.information(self, "完成", "视频分析完成，结果视频已生成并开始播放。")

    def _set_buttons_enabled(self, enabled):
        self.start_btn.setEnabled(enabled)
        self.open_btn.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)
