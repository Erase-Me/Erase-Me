import os
import sys
from PyQt5.QtWidgets import QApplication, QStackedWidget
from PyQt5.QtGui import QFontDatabase, QFont, QIcon

from intro_window import IntroWindow
from function_window import FunctionWindow
from select_window import SelectionWindow

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class MainWindow(QStackedWidget):
    def __init__(self):
        super().__init__()

        self.intro = IntroWindow(self.route_from_intro)
        self.selection = SelectionWindow(self.show_function_screen)
        self.function = FunctionWindow(self.back_to_selection)

        self.addWidget(self.intro)
        self.addWidget(self.selection)
        self.addWidget(self.function)

        self.setWindowTitle("Erase Me")
        self.setWindowIcon(QIcon(resource_path('public/icon.png')))
        self.resize(1000, 700)

        self.setCurrentIndex(0)
        self.show()

    def route_from_intro(self):
        if os.path.exists("selected_fields.json"):
            self.show_function_screen()
        else:
            self.setCurrentIndex(1)

    def show_function_screen(self):
        self.function.reload_selected_fields()
        self.setCurrentIndex(2)

    def back_to_selection(self):
        if os.path.exists("selected_fields.json"):
            os.remove("selected_fields.json")
        self.setCurrentIndex(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    font_path = resource_path("public/Pretendard-Regular.otf")
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id != -1:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 12))

    def clean_masking_record():
        for path in ["masking_record_text.json", "masking_record_code.json"]:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("{}")
                print(f"🧼 {path} 내용 초기화 완료")
            except Exception as e:
                print(f"❌ {path} 초기화 실패: {e}")
    
    def cleanup_masking_record():
        for path in ["masking_record_text.json", "masking_record_code.json"]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"🧹 {path} 삭제 완료")
                except Exception as e:
                    print(f"❌ {path} 삭제 실패: {e}")
        
        log_path = "log.txt"
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
                print("🧹 log.txt 파일 삭제 완료")
            except Exception as e:
                print(f"❌ log.txt 삭제 실패: {e}")

    clean_masking_record()
    app.aboutToQuit.connect(cleanup_masking_record)

    win = MainWindow()
    sys.exit(app.exec_())