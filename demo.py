from pathlib import Path
import sys

from loguru import logger

from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QVBoxLayout,
    QLineEdit,
    QWidget,
)

from key_bus import GlobalKeyEventBus, VirtualKeyEventBus
from virtual_keyboard import VirtualKeyboard, VirtualLineEdit, VirtualTextEdit


class TestWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet("""
        QMainWindow {
            background: #f8f8ff;
        }
                           
        QLineEdit, QTextEdit { 
            background: #d8d8df;       
            border-radius: 6px;
            padding: 4px;
            border: 2px solid #d8d8df;
            color: #000000;
        }
                           
        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #608fff;
        }

        #VirtualKeyboard_Key_Std {
            background-color: #608fff;
            color: #0e0e0e;
            border-radius: 6px;
        }
        #VirtualKeyboard_Key_Std:hover {
            background-color: #709fff;
        }
        #VirtualKeyboard_Key_Std:pressed {
            background-color: #80afff;
        }
                           
        #VirtualKeyboard_Key_Tertiary {
            background-color: #3054ae;
            color: #ffffff;
            border-radius: 6px;
        }
        #VirtualKeyboard_Key_Tertiary:hover {
            background-color: #4064be;
        }
        #VirtualKeyboard_Key_Tertiary:pressed {
            background-color: #5074ce;
        }
                           
        #VirtualKeyboard_Key_Secondary {
            background-color: #102f7e;
            color: #ffffff;
            border-radius: 6px;
        }
        #VirtualKeyboard_Key_Secondary:hover {
            background-color: #203f8e;
        }
        #VirtualKeyboard_Key_Secondary:pressed {
            background-color: #304f9e;
        }
                           
        #VirtualKeyboard_Key_Primary {
            background-color: #000f2e;
            color: #ffffff;
            border-radius: 6px;
        }
        #VirtualKeyboard_Key_Primary:hover {
            background-color: #101f3e;
        }
        #VirtualKeyboard_Key_Primary:pressed {
            background-color: #202f4e;
        }
        """)

        self.global_input_bus = GlobalKeyEventBus()
        self.global_input_bus.add_source(self)
        self.global_input_bus.key_event.connect(
            lambda event: logger.debug(f"Global key: {event}")
        )

        self.virtual_input_bus = VirtualKeyEventBus()

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.root_layout = QVBoxLayout(self.widget)

        self.preview = VirtualLineEdit()
        self.preview.setPlaceholderText("Virtual keystrokes will appear here")
        self.root_layout.addWidget(self.preview)

        self.preview2 = VirtualTextEdit()
        self.preview2.setPlaceholderText("Virtual keystrokes will appear here")
        self.root_layout.addWidget(self.preview2)

        self.preview3 = VirtualLineEdit()
        self.preview3.setPlaceholderText("I don't need focus")
        self.preview3.require_focus = False # don't require focus - useful on some touch interfaces where there is only one input
        self.root_layout.addWidget(self.preview3)

        self.regular_line_edit = QLineEdit()
        self.regular_line_edit.setPlaceholderText("I'm just a regular Line Edit, not a virtual one")
        self.root_layout.addWidget(self.regular_line_edit)

        self.root_layout.addStretch()

        self.keyboard = VirtualKeyboard(Path("KeyboardLayouts/en-US.xml"))
        self.root_layout.addWidget(self.keyboard)

        self.show()


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="TRACE")
    app = QApplication(sys.argv)
    win = TestWindow()
    app.exec()
