import functools
from pathlib import Path
import string
import sys
from typing import Any, ClassVar
import unicodedata
import xml.etree.ElementTree as ET

from PySide6.QtGui import QKeyEvent
from loguru import logger

from PySide6.QtWidgets import QToolButton, QMainWindow, QApplication, QHBoxLayout, QVBoxLayout, QFrame, QWidget, QLabel, QStackedWidget, QLineEdit
from PySide6.QtCore import Signal, Qt
from fonticon_mdi7 import MDI7
from superqt.fonticon import icon

KEY_SIZE_W = 48
KEY_SIZE_H = 36

class VirtualKeyboardLineEdit(QLineEdit):
    def keyPressEvent(self, ev: QKeyEvent) -> None:
        ev.ignore()
        logger.trace(f"{self} rejected physical keyboard event, {ev.key()}")

    def connect_virtual(self, virt: "VirtualKeyboard"):
        virt.key_event.connect(self.key_slot)

    def key_slot(self, key: str):
        match key:
            case "backspace":
                self.backspace()
            case "return":
                pass # this doesn't really matter for a QLineEdit since there is only one line
            case _: # everything else
                self.insert(key)

class VirtualKeyboard(QFrame):
    key_event = Signal(str)
    instance: "ClassVar[VirtualKeyboard | None]" = None

    def __init__(self, root_layout_path: Path):
        super().__init__()
        if not VirtualKeyboard.instance:
            VirtualKeyboard.instance = self
        else:
            msg = "Only one VirtualKeyboard can be used at a time"
            raise RuntimeError(msg)
        
        self.root_layout_path = root_layout_path
        self.layouts_dir = root_layout_path.parent

        self.setObjectName(self.__class__.__name__)

        self.stack = QStackedWidget(self)
        
        self._layout_name_to_index: dict[str, int] = {}
        self._parsed_layouts_cache: dict[Path, dict[str, Any]] = {}
        self._root_layout_filename: str = self.root_layout_path.name

        main_frame_layout = QVBoxLayout(self)
        main_frame_layout.setContentsMargins(0, 0, 0, 0)
        main_frame_layout.addWidget(self.stack)
        self.setLayout(main_frame_layout)

        self._build_layouts(self.root_layout_path, self._root_layout_filename)

        if self._root_layout_filename in self._layout_name_to_index:
            self.stack.setCurrentIndex(self._layout_name_to_index[self._root_layout_filename])
            logger.info(f"Initial layout set to: {self._root_layout_filename}")
        else:
            logger.error(f"Root layout '{self._root_layout_filename}' not found in loaded layouts. Displaying empty keyboard.")
            if self.stack.count() == 0:
                self.stack.addWidget(QWidget())


    def get_layout_path(self, layout_filename: str) -> Path:
        return self.layouts_dir / layout_filename
    
    def _parse_layout_xml(self, path: Path) -> dict[str, Any] | None:
        if path in self._parsed_layouts_cache:
            return self._parsed_layouts_cache[path]

        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Error parsing XML file {path}: {e}")
            return None
        except FileNotFoundError:
            logger.error(f"Layout file not found: {path}")
            return None

        layout_name = root.get('name', 'Unknown Layout')
        logger.debug(f"Parsed XML for layout: {layout_name} from {path.name}")
        layout_data = {"layoutName": layout_name, "rows": []}

        for row_elem in root.findall('Row'):
            row_type = row_elem.get('type')
            row_elements = []

            for element in row_elem:
                if element.tag == 'Key':
                    key_data = {
                        "type": "key",
                        "symbol": element.get('symbol', ''),
                        "keystroke": element.get('keystroke'),
                        "width": float(element.get('width', 1.0))
                    }

                    layout_link = element.get('layoutLink')
                    if layout_link:
                        key_data["layoutLink"] = layout_link

                    row_elements.append(key_data)

                elif element.tag == 'Spacer':
                    spacer_data = {
                        "type": "spacer",
                        "width": float(element.get('width', 1.0))
                    }
                    row_elements.append(spacer_data)
            
            layout_data["rows"].append({"type": row_type, "elements": row_elements})
            
        self._parsed_layouts_cache[path] = layout_data
        return layout_data

    def _build_layouts(self, current_path: Path, current_link_name: str):
        if current_link_name in self._layout_name_to_index:
            logger.trace(f"Layout '{current_link_name}' already loaded")
            return

        logger.debug(f"Loading and building UI for layout: {current_link_name}")
        layout_data = self._parse_layout_xml(current_path)

        if layout_data is None:
            logger.error(f"Failed to load layout data for '{current_link_name}'. Cannot build UI.")
            return

        layout_widget = self._build_layout_widget(layout_data)
        
        index = self.stack.addWidget(layout_widget)
        self._layout_name_to_index[current_link_name] = index
        logger.debug(f"Added layout '{current_link_name}' to stacked widget at index {index}")

        for row in layout_data.get("rows", []):
            for element in row.get("elements", []):
                if element.get("type") == "key":
                    layout_link = element.get("layoutLink")
                    if layout_link:
                        if layout_link == "ROOT":
                            continue
                        
                        next_layout_path = self.get_layout_path(layout_link)
                        self._build_layouts(next_layout_path, layout_link) # yuck

    def _build_layout_widget(self, layout_data: dict[str, Any]) -> QWidget:
        widget = QWidget()
        ui_layout = QVBoxLayout(widget)

        for row in layout_data["rows"]:
            row_layout = QHBoxLayout()
            row_layout.addStretch()

            for element in row["elements"]:
                match element["type"]:
                    case "spacer":
                        logger.trace(f"Adding spacing, {element['width']}")
                        row_layout.addSpacing(int(element["width"] * KEY_SIZE_W))
                    case "key":
                        button = QToolButton()
                        button.setFocusPolicy(Qt.FocusPolicy.NoFocus) # don't allow the real keyboard to press keys on the virtual keyboard
                        match element["symbol"]:
                            case "ICON_SHIFT":
                                button.setIcon(icon(MDI7.arrow_up_bold_outline, color=self.palette().text().color().name()))
                            case "ICON_UNSHIFT":
                                button.setIcon(icon(MDI7.arrow_up_bold, color=self.palette().text().color().name()))
                            case "ICON_BKSP":
                                button.setIcon(icon(MDI7.keyboard_backspace, color=self.palette().text().color().name()))
                            case _:
                                button.setText(element["symbol"].replace("&", "&&")) # Qt needs to have `&` escaped
                        
                        layout_link = element.get("layoutLink")
                        if layout_link:
                            if layout_link == "ROOT":
                                target_link_name = self._root_layout_filename
                            else:
                                target_link_name = layout_link
                            
                            button.clicked.connect(functools.partial(self._switch_to_layout, target_link_name))
                            logger.trace(f"Key '{element['symbol']}' links to layout '{target_link_name}'")
                        elif element["keystroke"]:
                            if element["keystroke"]:
                                button.clicked.connect(functools.partial(self.key_event.emit, element['keystroke']))
                                logger.trace(f"Key '{element['symbol']}' emits keystroke '{element['keystroke']}'")
                            else:
                                logger.warning(f"Key '{element['symbol']}' has an empty keystroke list.")
                        else:
                            logger.warning(f"Key '{element['symbol']}' has no keystroke or layoutLink defined.")

                        row_layout.addWidget(button)
                        button.setFixedSize(max(int(KEY_SIZE_W * element["width"]), button.minimumSizeHint().width()), KEY_SIZE_H) # must be after addWidget
            
            row_layout.addStretch()
            ui_layout.addLayout(row_layout)
        
        widget.setLayout(ui_layout)
        return widget

    def _switch_to_layout(self, target_layout_link_name: str):
        if target_layout_link_name not in self._layout_name_to_index:
            logger.error(f"Attempted to switch to unknown layout: '{target_layout_link_name}'")
            return

        target_index = self._layout_name_to_index[target_layout_link_name]
        self.stack.setCurrentIndex(target_index)
        logger.debug(f"Switched to layout: {target_layout_link_name}")


class TestWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.root_layout = QVBoxLayout(self.widget)

        self.physical = QLineEdit()
        self.physical.setPlaceholderText("Physical keystrokes will appear here only when focus is given")
        self.root_layout.addWidget(self.physical)

        self.physical_always = QLineEdit()
        self.physical_always.setPlaceholderText("Physical keystrokes will ALWAYS appear here NO MATTER WHAT FOCUS IS GIVEN")
        self.physical_always.keyPressEvent = lambda *_: None # this will force the line edit to ignore keystrokes - they will be injected below
        self.grabKeyboard() # redirect all key events to keyPressEvent defined below
        self.physical_always.mouseMoveEvent = lambda *_: None # I can't find a way around this: prevent selection
        self.physical_always.mouseDoubleClickEvent = lambda *_: None # I can't find a way around this: prevent selection
        self.physical_always.mousePressEvent = lambda *_: None # I can't find a way around this: prevent selection
        self.physical_always.mouseReleaseEvent = lambda *_: None # I can't find a way around this: prevent selection
        self.physical_always.focusInEvent = lambda *_: self.physical_always.setSelection(len(self.physical_always.text()),len(self.physical_always.text())) # I can't find a way around this: prevent selection
        self.root_layout.addWidget(self.physical_always)

        self.preview = VirtualKeyboardLineEdit()
        self.preview.setPlaceholderText("Virtual keystrokes will appear here")
        self.root_layout.addWidget(self.preview)

        self.root_layout.addStretch()

        self.keyboard = VirtualKeyboard(Path("KeyboardLayouts/en-US.xml"))
        self.preview.connect_virtual(self.keyboard)
        self.root_layout.addWidget(self.keyboard)

        self.show()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        The global event for the phyical keyboard.
        Almost all keys that are recognized by your OS/X11/Wayland are passed through this function
        """

        # kinda janky, but it seems to work perfectly
        # do this before everything else
        focused = self.focusWidget()
        if hasattr(focused, "keyPressEvent"):
            focused.keyPressEvent(event)
        event.accept()

        if event.key() == Qt.Key.Key_Backspace: # some keys like backspace need to be treated differently
            self.physical_always.backspace()
            return
        elif event.key() == Qt.Key.Key_Return:
            # maybe we can do something with the tag here?
            logger.info("Global physical return pressed")
            return # this also causes issues with the line edit
        elif 0x110000 > event.key() and (unicodedata.category(chr(event.key())) not in ["c"]):
            self.physical_always.insert(event.text())


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="TRACE")
    app = QApplication(sys.argv)
    win = TestWindow()
    app.exec()