import sys
import os
import json
import subprocess
import datetime
import requests
from PyQt5.QtWidgets import QLabel, QScrollArea
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from dotenv import load_dotenv

from masking.text_masking import load_mask_tags_from_selection

CREATE_NO_WINDOW = 0x08000000 

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class ImageUploadWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, server_url, file_path, save_folder):
        super().__init__()
        self.server_url = server_url
        self.file_path = file_path
        self.save_folder = save_folder

    def run(self):
        try:
            with open(self.file_path, "rb") as f:
                files = {"image": (os.path.basename(self.file_path), f, "image/png")}
                # 추가: 선택된 태그 불러와서 서버에 함께 전달
                mask_tags = list(load_mask_tags_from_selection())
                data = {"mask_tags": ",".join(mask_tags)}

                response = requests.post(self.server_url, files=files, data=data)

            if response.status_code == 200:
                os.makedirs(self.save_folder, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                save_name = f"masked_{timestamp}_{os.path.basename(self.file_path)}"
                save_path = os.path.join(self.save_folder, save_name)
                with open(save_path, "wb") as out:
                    out.write(response.content)
                self.finished.emit(save_path)
            else:
                self.error.emit(f"❌ 서버 오류: {response.status_code}")
        except Exception as e:
            self.error.emit(f"❌ 요청 실패: {e}")

class FunctionWindow(QWidget):
    def __init__(self, back_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.mask_targets = []

        self.text_proc = None
        self.img_proc = None

        self.reload_selected_fields()
        self.initUI()

    def reload_selected_fields(self):
        if os.path.exists("selected_fields.json"):
            with open("selected_fields.json", "r", encoding="utf-8") as f:
                self.mask_targets = json.load(f)
        else:
            self.mask_targets = []

        print("불러온 마스킹 대상:", self.mask_targets)

    def initUI(self):
        logo = QPixmap(resource_path("public/logo.png"))
        self.logo_label = QLabel()
        self.logo_label.setPixmap(logo.scaled(240, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.btn_text = QPushButton("텍스트 자동 마스킹 (OFF)")
        self.btn_text.setCheckable(True)
        self.btn_text.setFixedSize(450, 50)
        self.btn_text.clicked.connect(self.toggle_text_masking_process)
        self.btn_text.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
                color: #3e5879;
                font-weight: bold;
                font-size: 18px;
                font-family: Pretendard;
                border: 1px solid #3e5879;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:checked {
                background-color: #3e5879;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #acbacb;
            }
        """)

        self.btn_image_masking = QPushButton("이미지 자동 마스킹 (OFF)")
        self.btn_image_masking.setCheckable(True)
        self.btn_image_masking.setFixedSize(450, 50)
        self.btn_image_masking.clicked.connect(self.toggle_image_masking_process)
        self.btn_image_masking.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
                color: #3e5879;
                font-weight: bold;
                font-size: 18px;
                font-family: Pretendard;
                border: 1px solid #3e5879;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:checked {
                background-color: #3e5879;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #acbacb;
            }
        """)

        self.btn_image = QPushButton("이미지 업로드")
        self.btn_voice = QPushButton("음성 업로드")
        self.btn_image.setCheckable(True)
        self.btn_voice.setCheckable(True)
        self.btn_image.setChecked(True)

        self.btn_image.setFixedSize(450, 50)
        self.btn_voice.setFixedSize(450, 50)
        self.btn_image.clicked.connect(self.select_image)
        self.btn_voice.clicked.connect(self.select_voice)
        self.update_button_style()

        self.stack = QStackedWidget()
        self.image_page = self.build_image_page()
        self.voice_page = self.build_voice_page()
        self.stack.addWidget(self.image_page)
        self.stack.addWidget(self.voice_page)

        hbox_masking = QHBoxLayout()
        hbox_masking.setSpacing(10)
        hbox_masking.setContentsMargins(0, 10, 0, 0)
        hbox_masking.addWidget(self.btn_text)
        hbox_masking.addWidget(self.btn_image_masking)

        hbox_result_tap = QHBoxLayout()
        hbox_result_tap.setSpacing(10)
        hbox_result_tap.setContentsMargins(0, 20, 0, 0)
        hbox_result_tap.addWidget(self.btn_image)
        hbox_result_tap.addWidget(self.btn_voice)

        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.addWidget(self.logo_label)
        vbox.addSpacing(30)
        vbox.addLayout(hbox_masking)
        vbox.addLayout(hbox_result_tap)

        vbox.addWidget(self.stack)

        self.stack.setStyleSheet("""
            QStackedWidget {
                background-color: #ffffff;
                border: 1px solid #3e5879;
                border-radius: 8px;
            }
        """)

        self.code_mode_btn = QPushButton("코드 모드 (OFF)")
        self.code_mode_btn.setCheckable(True)
        self.code_mode_btn.setChecked(False)
        self.code_mode_btn.setFixedSize(150, 47)
        self.code_mode_btn.clicked.connect(self.toggle_code_mode)
        self.code_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
                color: #3e5879;
                font-weight: bold;
                font-size: 15px;
                font-family: Pretendard;
                border: 1px solid #3e5879;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:checked {
                background-color: #3e5879;
                color: white;
            }
            QPushButton:hover {
                background-color: #acbacb;
            }
        """)

        self.redo_btn = QPushButton("텍스트 마스킹 범위 재설정")
        self.redo_btn.setFixedSize(200, 47)
        self.redo_btn.clicked.connect(self.handle_back_to_selection)
        self.redo_btn.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
                color: #3e5879;
                font-weight: bold;
                font-size: 15px;
                font-family: Pretendard;
                border: 1px solid #3e5879;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #acbacb;
            }
        """)

        hbox_buttons = QHBoxLayout()
        hbox_buttons.setContentsMargins(0, 20, 0, 0)
        hbox_buttons.addWidget(self.redo_btn)
        hbox_buttons.addStretch()
        hbox_buttons.addWidget(self.code_mode_btn)
        vbox.addLayout(hbox_buttons)

        self.setLayout(vbox)
        self.setWindowTitle("Erase Me")
        self.resize(1000, 700)
        self.stack.setCurrentIndex(0)
        self.show()

    def toggle_text_masking_process(self):
        if self.btn_text.isChecked():
            if self.code_mode_btn.isChecked():
                script_path = resource_path("masking/code_masking.pyw")
                print("🚀 코드 모드: code_masking.py 실행")
            else:
                script_path = resource_path("masking/text_masking.pyw")
                print("🚀 일반 모드: text_masking.py 실행")

            self.text_proc = subprocess.Popen(
                ["pythonw", script_path],
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW
            )
            self.btn_text.setText("텍스트 자동 마스킹 (ON)")

        else:
            if self.text_proc:
                self.text_proc.terminate()
                self.text_proc = None
                print("🛑 텍스트 마스킹 프로그램 종료됨")
            self.btn_text.setText("텍스트 자동 마스킹 (OFF)")
    
    def toggle_code_mode(self):
        if self.code_mode_btn.isChecked():
            self.code_mode_btn.setText("코드 모드 (ON)")
            print("🧠 코드 모드 활성화됨")
        else:
            self.code_mode_btn.setText("코드 모드 (OFF)")
            print("📝 일반 텍스트 모드로 전환됨")

        if self.btn_text.isChecked():
            if self.text_proc:
                self.text_proc.terminate()
                self.text_proc = None
                print("🔄 텍스트 마스킹 프로세스 재시작 중...")

            if self.code_mode_btn.isChecked():
                script_path = resource_path("masking/code_masking.pyw")
                print("▶️ 코드 모드로 재실행: code_masking.py")
            else:
                script_path = resource_path("masking/text_masking.pyw")
                print("▶️ 일반 모드로 재실행: text_masking.py")

            self.text_proc = subprocess.Popen(
                ["pythonw", script_path],
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW
            )

    def toggle_image_masking_process(self):
        if self.btn_image_masking.isChecked():
            self.update_button_style()
            
            if self.img_proc is None:
                script_path = resource_path("masking/img_masking.pyw")
                mode = "code" if self.code_mode_btn.isChecked() else "text"
                env = os.environ.copy()
                env["MASK_MODE"] = mode

                self.img_proc = subprocess.Popen(
                    ["pythonw", script_path],
                    env=env,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
                print(f"🚀 이미지 마스킹 프로그램 실행됨 ({mode} 모드)")
                self.btn_image_masking.setText("이미지 자동 마스킹 (ON)")
            else:
                print("이미 이미지 마스킹 프로그램이 실행 중입니다.")
        else:
            self.update_button_style()
            if self.img_proc:
                self.img_proc.terminate()
                self.img_proc = None
                print("🛑 이미지 마스킹 프로그램 종료됨")
            self.btn_image_masking.setText("이미지 자동 마스킹 (OFF)")
        
    def handle_back_to_selection(self):
        if os.path.exists("selected_fields.json"):
            os.remove("selected_fields.json")
        if self.back_callback:
            self.back_callback()

    def build_image_page(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        label = QLabel("🖼️ 이미지 업로드")
        label.setAlignment(Qt.AlignCenter)

        self.img_file_label = QLabel("선택된 파일 없음")
        self.img_file_label.setAlignment(Qt.AlignCenter)

        self.image_upload_btn = QPushButton("이미지 선택")
        self.image_upload_btn.setFixedWidth(200)
        self.image_upload_btn.clicked.connect(self.upload_image)

        self.img_preview = QLabel()
        self.img_preview.setFixedSize(600, 400)
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.hide()

        self.copy_btn = QPushButton("마스킹 이미지 클립보드 복사")
        self.copy_btn.setFixedWidth(350)
        self.copy_btn.clicked.connect(self.copy_preview_image_to_clipboard)
        self.copy_btn.hide()

        layout.addWidget(label, alignment=Qt.AlignCenter)
        layout.addWidget(self.image_upload_btn, alignment=Qt.AlignCenter)
        layout.addWidget(self.img_file_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.img_preview, alignment=Qt.AlignCenter)
        layout.addWidget(self.copy_btn, alignment=Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def build_voice_page(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        self.final_masked_result = ""

        label = QLabel("🎤 음성 파일 업로드")
        label.setAlignment(Qt.AlignCenter)
        #label.setStyleSheet("margin-top: 46px;")

        self.voice_file_label = QLabel("선택된 파일 없음")
        self.voice_file_label.setAlignment(Qt.AlignCenter)

        self.upload_btn = QPushButton("음성 파일 선택")  # 클래스 변수
        self.upload_btn.setFixedWidth(200)
        self.upload_btn.clicked.connect(self.upload_voice)

        self.scroll_label = QLabel()
        self.scroll_label.setText("⏳ 마스킹 처리 중...")
        self.scroll_label.setWordWrap(True)
        self.scroll_label.setAlignment(Qt.AlignCenter)
        self.scroll_label.setStyleSheet("""
            QLabel {
                color: #3e5879;
                font-size: 15px;
                padding: 8px;
                line-height: 1.5em;
            }
        """)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(180)
        self.scroll_area.setWidget(self.scroll_label)
        self.scroll_area.hide()
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ccc;
                border-radius: 6px;
                background: #fff;

            }
        """)

        self.copy_result_btn = QPushButton("마스킹 결과 복사")
        self.copy_result_btn.setFixedWidth(200)
        self.copy_result_btn.clicked.connect(self.copy_masked_result)
        self.copy_result_btn.hide()

        self.reupload_btn = QPushButton("다시 업로드하기")
        self.reupload_btn.setFixedWidth(200)
        self.reupload_btn.clicked.connect(self.reset_voice_page)
        self.reupload_btn.hide()

        layout.addWidget(label, alignment=Qt.AlignCenter)
        layout.addWidget(self.upload_btn, alignment=Qt.AlignCenter)
        layout.addWidget(self.voice_file_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.copy_result_btn, alignment=Qt.AlignCenter)
        layout.addWidget(self.reupload_btn, alignment=Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def reset_voice_page(self):
        self.voice_file_label.setText("선택된 파일 없음")
        self.scroll_label.setText("")
        self.scroll_area.hide()
        self.copy_result_btn.hide()
        self.reupload_btn.hide()

        self.upload_btn.show()
        self.voice_file_label.show()

    def upload_image(self):
        if self.code_mode_btn.isChecked():
            server_url = os.getenv("IMG_MASKING_SERVER_URL_CODE")
            print("[디버그] 코드 모드: CODE 서버로 요청")
        else:
            server_url = os.getenv("IMG_MASKING_SERVER_URL_TEXT")
            print("[디버그] 일반 모드: TEXT 서버로 요청")
        if not server_url:
            QMessageBox.critical(self, "에러", "❌ {env_key}  환경 변수가 설정되지 않았습니다.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if not file_path:
            self.img_file_label.setText("선택된 파일 없음")
            self.img_preview.clear()
            self.img_preview.hide()
            self.copy_btn.hide()
            return

        self.img_file_label.setText(f"선택된 이미지: {os.path.basename(file_path)}")
        self.img_preview.clear()
        self.img_preview.setText("⏳ 마스킹 처리 중...")
        self.img_preview.show()
        self.copy_btn.hide()

        self.image_upload_btn.hide()

        self.upload_worker = ImageUploadWorker(server_url, file_path, "masked_images")
        self.upload_worker.finished.connect(self.display_masked_image)
        self.upload_worker.error.connect(self.display_error)
        self.upload_worker.start()


    def display_masked_image(self, save_path):
        pixmap = QPixmap(save_path).scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_preview.setPixmap(pixmap)
        self.copy_btn.show()
        self.image_upload_btn.show()

    def display_error(self, error_message):
        self.img_preview.setText(error_message)
        self.image_upload_btn.show()
    
    def copy_preview_image_to_clipboard(self):
        if not self.img_preview.pixmap():
            return
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.img_preview.pixmap())
        print("✅ 미리보기 이미지를 클립보드에 복사했습니다.")

    def upload_voice(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "음성 선택", "", "Audio Files (*.mp3 *.wav *.m4a)")
        if os.path.exists("log.txt"):
            os.remove("log.txt")

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.update_log_display)
        self.log_timer.start(1000)
        if file_path:
            self.voice_file_label.setText(f"선택된 음성: {file_path.split('/')[-1]}")
            self.sender().hide()
            self.voice_file_label.hide()
            self.scroll_label.setText("⏳ 마스킹 처리 중...")
            self.scroll_area.show()

            result_path = "masked_result.txt"
            if os.path.exists(result_path):
                os.remove(result_path)

            script_path = resource_path("masking/audio_masking.pyw")
            try:
                subprocess.Popen(
                    ["pythonw", script_path, "--source", file_path],
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
                print("🎤 audio_masking.py 실행됨")

                self.check_result_timer = QTimer(self)
                self.check_result_timer.timeout.connect(self.check_masking_result)
                self.check_result_timer.start(2000)

            except Exception as e:
                print(f"❌ audio_masking.py 실행 실패: {e}")

    def update_log_display(self):
        if os.path.exists("log.txt"):
            with open("log.txt", "r", encoding="utf-8") as f:
                lines = f.read().strip()
            self.scroll_label.setText(lines)

    def check_masking_result(self):
        result_path = "masked_result.txt"
        if os.path.exists(result_path):
            with open(result_path, "r", encoding="utf-8") as f:
                result_text = f.read().strip()
            self.final_masked_result = result_text
            self.scroll_label.setText(f"🛡️ 마스킹 결과:\n{result_text}")
            self.copy_result_btn.show()
            self.reupload_btn.show()
            self.check_result_timer.stop()
            self.log_timer.stop()

    def copy_masked_result(self):
        clipboard = QApplication.clipboard()
        if self.final_masked_result:
            clipboard.setText(self.final_masked_result.strip())
            print("📋 마스킹 결과 복사 완료")
        else:
            print("⚠️ 복사할 마스킹 결과가 없습니다.")

    def select_image(self):
        self.btn_image.setChecked(True)
        self.btn_voice.setChecked(False)
        self.stack.setCurrentIndex(0)
        self.update_button_style()

    def select_voice(self):
        self.btn_voice.setChecked(True)
        self.btn_image.setChecked(False)
        self.stack.setCurrentIndex(1)
        self.update_button_style()
    
    def closeEvent(self, event):
        if self.text_proc:
            self.text_proc.terminate()
            print("🛑 텍스트 마스킹 프로세스도 함께 종료됨")

        log_path = "log.txt"
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
                print("🧹 log.txt 파일 삭제 완료")
            except Exception as e:
                print(f"❌ log.txt 삭제 실패: {e}")

        event.accept()

    def update_button_style(self):
        active = """
            QPushButton {
                background-color: #3e5879;
                color: white;
                font-weight: bold;
                font-size: 18px;
                font-family: Pretendard;
                border: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #576981;
            }
        """
        inactive = """
            QPushButton {
                background-color: #ffffff;
                color: #3e5879;
                font-weight: bold;
                font-size: 18px;
                font-family: Pretendard;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #acbacb;
            }
        """

        self.btn_image.setStyleSheet(active if self.btn_image.isChecked() else inactive)
        self.btn_voice.setStyleSheet(active if self.btn_voice.isChecked() else inactive)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    font_id = QFontDatabase.addApplicationFont(resource_path("public/Pretendard-Regular.otf"))
    if font_id == -1:
        print("❌ Pretendard 폰트 로딩 실패")
    else:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            app.setFont(QFont(font_families[0], 12))
    
    ex = FunctionWindow()
    sys.exit(app.exec_())