from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QCheckBox, QPushButton, QGroupBox
from PyQt5.QtCore import Qt
import json

class SelectionWindow(QWidget):
    def __init__(self, next_callback):
        super().__init__()
        self.next_callback = next_callback
        self.initUI()

    def initUI(self):
        self.text_items = {}
        self.code_items = {}

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        layout.addWidget(QLabel("📄 텍스트"))

        text_box = QGroupBox()
        text_grid = QGridLayout()
        text_labels = ["이름", "주민등록번호", "전화번호", "이메일", "날짜", "시간", "장소", "기관"]

        for i, label in enumerate(text_labels):
            cb = QCheckBox(label)
            self.text_items[label] = cb
            row = i // 4
            col = i % 4
            text_grid.addWidget(cb, row, col)

        text_box.setLayout(text_grid)
        layout.addWidget(text_box)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        next_btn = QPushButton("다음")
        next_btn.setStyleSheet("""
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
        next_btn.setFixedSize(100, 40)
        next_btn.clicked.connect(self.on_next_clicked)
        btn_layout.addWidget(next_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def on_next_clicked(self):
        selected = self.get_selected_items()
        with open("selected_fields.json", "w", encoding="utf-8") as f:
            json.dump(selected, f, ensure_ascii=False, indent=2)
        self.next_callback()

    def get_selected_items(self):
        return [cb.text() for cb in {**self.text_items, **self.code_items}.values() if cb.isChecked()]
