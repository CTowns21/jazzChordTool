#!/usr/bin/env python3
"""
Module Name: mainWindow.py
Description: Main window for jazzChordTool GUI
Author: Carson Towns
"""

import copy
import time

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sessionModel import Session
from voicingEngine import STYLES


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jazz Chord Voicer")
        self.resize(980, 520)

        self.session = Session()
        self.revision = 0
        self.active_thread = None
        self.active_worker = None
        self.last_compute_started = None

        self._build_ui()
        self._wire_events()
        self.request_recompute()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        layout.addLayout(top)

        top.addWidget(QLabel("Chord:"))

        self.chord_input = QLineEdit()
        self.chord_input.setPlaceholderText("e.g. Dm7 or Ebmaj7/G")
        top.addWidget(self.chord_input)

        top.addWidget(QLabel("Pin:"))

        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("optional, e.g. typeB")
        top.addWidget(self.pin_input)

        self.add_button = QPushButton("Add")
        top.addWidget(self.add_button)

        top.addWidget(QLabel("Style:"))

        self.style_combo = QComboBox()
        self.style_combo.addItems(STYLES.keys())
        top.addWidget(self.style_combo)

        self.undo_button = QPushButton("Undo")
        top.addWidget(self.undo_button)

        self.delete_button = QPushButton("Delete Selected")
        top.addWidget(self.delete_button)

        self.pin_selected_button = QPushButton("Pin Selected")
        top.addWidget(self.pin_selected_button)

        self.unpin_selected_button = QPushButton("Unpin Selected")
        top.addWidget(self.unpin_selected_button)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "Chord", "Bass", "Voicing", "Notes", "Pinned"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _wire_events(self):
        self.add_button.clicked.connect(self.on_add)
        self.undo_button.clicked.connect(self.on_undo)
        self.delete_button.clicked.connect(self.on_delete_selected)
        self.pin_selected_button.clicked.connect(self.on_pin_selected)
        self.unpin_selected_button.clicked.connect(self.on_unpin_selected)
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        self.chord_input.returnPressed.connect(self.on_add)
        self.pin_input.returnPressed.connect(self.on_add)

    def on_add(self):
        symbol = self.chord_input.text().strip()
        pin = self.pin_input.text().strip() or None
        if not symbol:
            return

        try:
            self.session.add_chord(symbol, pin)
        except Exception as e:
            QMessageBox.warning(self, "Add chord", str(e))
            return

        self.chord_input.clear()
        self.pin_input.clear()
        self.request_recompute()

    def on_undo(self):
        self.session.remove_last()
        self.request_recompute()

    def on_delete_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.session.chords):
            return

        try:
            self.session.delete_at(row)
        except Exception as e:
            QMessageBox.warning(self, "Delete chord", str(e))
            return

        self.request_recompute()

    def on_pin_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        label = self.pin_input.text().strip()
        if not label:
            QMessageBox.information(self, "Pin chord", "Enter a voicing label in the Pin field.")
            return

        try:
            self.session.pin_chord(row, label)
        except Exception as e:
            QMessageBox.warning(self, "Pin chord", str(e))
            return

        self.request_recompute()

    def on_unpin_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        try:
            self.session.unpin_chord(row)
        except Exception as e:
            QMessageBox.warning(self, "Unpin chord", str(e))
            return

        self.request_recompute()

    def on_style_changed(self, style_name):
        try:
            self.session.set_style(style_name)
        except Exception as e:
            QMessageBox.warning(self, "Style", str(e))
            return

        self.request_recompute()

    def request_recompute(self):
        from workers import RecomputeWorker

        self.revision += 1
        revision = self.revision
        session_copy = copy.deepcopy(self.session)
        self.last_compute_started = time.perf_counter()

        if self.active_thread is not None and self.active_thread.isRunning():
            self.active_thread.quit()
            self.active_thread.wait()

        self.active_thread = QThread()
        self.active_worker = RecomputeWorker(revision, session_copy)
        self.active_worker.moveToThread(self.active_thread)

        self.active_thread.started.connect(self.active_worker.run)
        self.active_worker.finished.connect(self.on_recompute_finished)
        self.active_worker.finished.connect(self.active_thread.quit)
        self.active_worker.finished.connect(self.active_worker.deleteLater)
        self.active_thread.finished.connect(self.active_thread.deleteLater)

        self.status.showMessage("Recomputing...")
        self.active_thread.start()

    def on_recompute_finished(self, revision, rows, error):
        if revision != self.revision:
            return

        if error:
            self.status.showMessage(f"Error: {error}", 5000)
            return

        self.populate_table(rows)

        if self.last_compute_started is not None:
            elapsed_ms = (time.perf_counter() - self.last_compute_started) * 1000
            self.status.showMessage(f"Ready · recomputed in {elapsed_ms:.1f} ms")
        else:
            self.status.showMessage("Ready")

    def populate_table(self, rows):
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            values = [
                str(row["index"]),
                row["symbol"],
                row["bass"],
                row["voicing"],
                row["notes"],
                "Yes" if row["pinned"] else "",
            ]

            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if c == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
