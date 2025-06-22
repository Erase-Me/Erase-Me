import os
import sys
import time
import datetime
import requests
from PIL import Image
from dotenv import load_dotenv
from text_masking import load_mask_tags_from_selection
import json

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTabWidget, QMessageBox
)
from PyQt5.QtGui import QPixmap, QFontDatabase, QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

interrupt_delay = 5000

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

class MaskingWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, server_url, img_data, save_path):
        super().__init__()
        self.server_url = server_url
        self.img_data = img_data
        self.save_path = save_path

    def run(self):
        try:
            files = {"image": ("clipboard.png", self.img_data, "image/png")}
            mask_tags = list(load_mask_tags_from_selection())
            data = {"mask_tags": ",".join(mask_tags)}
            print(f"[디버그] 요청 URL: {self.server_url}")
            print(f"[디버그] 요청 태그: {data}")
            res = requests.post(self.server_url, files=files, data=data)
            print(f"[디버그] 응답 상태코드: {res.status_code}")
            print(f"[디버그] 응답 내용: {res.text[:200]}...")
            if res.status_code == 200:
                with open(self.save_path, "wb") as out:
                    out.write(res.content)
                self.finished.emit(self.save_path)
            else:
                self.error.emit(f"❌ 서버 오류: {res.status_code}")
        except Exception as e:
            self.error.emit(f"❌ 요청 실패: {e}")

class ImageMaskingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Erase Me: Image Masking")
        self.resize(600, 500)

        load_dotenv(dotenv_path=resource_path(".env"))
        mode = os.getenv("MASK_MODE", "text")

        if mode == "code":
            self.server_url = os.getenv("IMG_MASKING_SERVER_URL_CODE")
        else:
            self.server_url = os.getenv("IMG_MASKING_SERVER_URL_TEXT") 
        print(f"[디버그] 현재 마스킹 모드: {mode}")
        print(f"[디버그] 서버 URL 설정됨: {self.server_url}")
        
        if not self.server_url:
            QMessageBox.critical(self, "에러", "❌ IMG_MASKING_SERVER_URL 환경 변수가 설정되지 않았습니다.")
            sys.exit(1)

        font_path = resource_path("public/Pretendard-Regular.otf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app_font = QFont(font_family)
            app_font.setPointSize(app_font.pointSize() + 1)
            QApplication.setFont(app_font)

        self.layout = QVBoxLayout()

        self.status_label = QLabel("👀 이미지 클립보드 감시 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        self.masked_image_label = QLabel("마스킹된 이미지가 여기에 표시됩니다.")
        self.masked_image_label.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(self.masked_image_label, "마스킹 결과")
        self.layout.addWidget(self.tabs)

        self.copy_button = QPushButton("마스킹 이미지 클립보드 복사")
        self.copy_button.setMinimumHeight(50)
        self.copy_button.clicked.connect(self.copy_image_to_clipboard)
        self.copy_button.setEnabled(False)
        self.layout.addWidget(self.copy_button)

        self.setLayout(self.layout)

        clipboard = QApplication.clipboard()
        self.last_clip = clipboard.pixmap()
        self.is_processing = False
        self.is_internal_copy = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.monitor_clipboard)
        self.timer.start(500)

    def monitor_clipboard(self):
        if self.is_processing or self.is_internal_copy:
            return

        clipboard = QApplication.clipboard()
        img = clipboard.pixmap()
        if img and not img.isNull() and (self.last_clip is None or img.toImage() != self.last_clip.toImage()):
            self.last_clip = img

            buffer = img.toImage().bits().asstring(img.width() * img.height() * 4)
            qimage = img.toImage()
            byte_array = qimage.bits().asstring(qimage.byteCount())
            image = Image.frombytes("RGBA", (qimage.width(), qimage.height()), byte_array)
            img_data = self.qimage_to_bytes(qimage)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("masked_images", exist_ok=True)
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            save_dir = os.path.join(desktop_path, "EraseMe_Masked")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"masked_{timestamp}.png")
            print(f"✅ 서버 요청 준비 완료: {save_path}")

            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
            self.raise_()
            self.activateWindow()

            self.masked_image_label.setText("⏳ 서버로 이미지 전송 중...")
            self.copy_button.setEnabled(False)

            self.is_processing = True
            self.worker = MaskingWorker(
                self.server_url,
                img_data,
                save_path
            )
            self.worker.finished.connect(self.update_masked_image)
            self.worker.error.connect(self.show_error)
            self.worker.start()

    def qimage_to_bytes(self, qimage):
        from PyQt5.QtCore import QBuffer, QByteArray
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        qimage.save(buffer, "PNG")
        return buffer.data()

    def update_masked_image(self, path):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.masked_image_label.setPixmap(
                pixmap.scaled(500, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.copy_button.setEnabled(True)
        else:
            self.masked_image_label.setText("❌ 이미지 로딩 실패")
            self.copy_button.setEnabled(False)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()
        self.is_processing = False

        self.is_internal_copy = True
        QTimer.singleShot(interrupt_delay, self.reset_internal_copy)

    def reset_internal_copy(self):
        self.is_internal_copy = False

    def show_error(self, message):
        QMessageBox.critical(self, "에러", message)
        self.masked_image_label.setText("❌ 서버 요청 실패")
        self.copy_button.setEnabled(False)
        self.is_processing = False

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def copy_image_to_clipboard(self):
        clipboard = QApplication.clipboard()
        pixmap = self.masked_image_label.pixmap()
        if pixmap:
            clipboard.setPixmap(pixmap)
            self.last_clip = clipboard.pixmap() 
            QMessageBox.information(self, "성공", "마스킹 이미지를 클립보드에 복사했습니다.")
        else:
            QMessageBox.warning(self, "오류", "❌ 복사할 이미지가 없습니다.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageMaskingApp()
    window.show()
    sys.exit(app.exec_())