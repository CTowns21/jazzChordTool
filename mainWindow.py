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
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
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

from chordParser import parseChordSymbol
from pianoWidget import PianoWidget
from sessionModel import Session
from voicingEngine import STYLES, availableLabels
from workers import RecomputeWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jazz Chord Voicer")
        self.resize(1180, 720)

        self.session = Session()
        self.revision = 0
        self.active_thread = None
        self.active_worker = None
        self.last_compute_started = None
        self.pending_select_row = None

        self.current_rows = []
        self.current_voicings = []

        self._build_ui()
        self._wire_events()
        self.request_recompute()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        # Input and application controls
        top = QHBoxLayout()
        outer.addLayout(top)

        top.addWidget(QLabel("Chord:"))

        self.chord_input = QLineEdit()
        self.chord_input.setPlaceholderText("e.g. Dm7 or Ebmaj7/G")
        top.addWidget(self.chord_input, 2)

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

        # Main content: table and chord controls above, piano below.
        body = QVBoxLayout()
        outer.addLayout(body, 1)

        top_row = QHBoxLayout()
        body.addLayout(top_row, 3)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["#", "Chord", "Bass", "Voicing", "Notes", "Pinned"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(180)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)

        for column in (0, 1, 2, 3, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 11pt;
            }
            QHeaderView::section {
                font-size: 11pt;
                font-weight: bold;
                padding: 6px;
            }
        """)
        self.table.verticalHeader().setDefaultSectionSize(30)
        top_row.addWidget(self.table, 1)

        self.selection_group = QGroupBox("Selected Chord")
        top_row.addWidget(self.selection_group, 1)

        selection_layout = QHBoxLayout(self.selection_group)

        form = QFormLayout()
        selection_layout.addLayout(form, 2)

        self.selected_index_label = QLabel("—")
        self.selected_symbol_label = QLabel("—")
        self.selected_bass_label = QLabel("—")
        self.selected_current_voicing_label = QLabel("—")
        self.selected_pin_status_label = QLabel("—")

        form.addRow("Row:", self.selected_index_label)
        form.addRow("Chord:", self.selected_symbol_label)
        form.addRow("Bass:", self.selected_bass_label)
        form.addRow("Current voicing:", self.selected_current_voicing_label)
        form.addRow("Pinned:", self.selected_pin_status_label)

        controls_layout = QVBoxLayout()
        selection_layout.addLayout(controls_layout, 3)

        controls_layout.addWidget(QLabel("Valid voicings for this chord:"))
        self.valid_voicing_combo = QComboBox()
        controls_layout.addWidget(self.valid_voicing_combo)

        self.pin_selected_button = QPushButton("Pin to Selected Voicing")
        controls_layout.addWidget(self.pin_selected_button)

        self.unpin_selected_button = QPushButton("Unpin")
        controls_layout.addWidget(self.unpin_selected_button)

        controls_layout.addWidget(QLabel("Quick add with optional pin:"))
        self.quick_pin_combo = QComboBox()
        self.quick_pin_combo.addItem("(no pin)")
        controls_layout.addWidget(self.quick_pin_combo)

        self.add_with_pin_button = QPushButton("Add Chord With Selected Pin")
        controls_layout.addWidget(self.add_with_pin_button)
        controls_layout.addStretch(1)

        piano_group = QGroupBox("Voicing on keyboard")
        piano_layout = QVBoxLayout(piano_group)

        legend_layout = QHBoxLayout()
        legend_items = (
            ("#4A90E2", "Root"),
            ("#E6A23C", "Guide tones (3, 7, 6)"),
            ("#67C23A", "Other chord tones / extensions"),
        )
        for color, text in legend_items:
            swatch = QWidget()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(
                f"background-color: {color}; border: 1px solid #555;"
            )
            legend_layout.addWidget(swatch)
            legend_layout.addWidget(QLabel(text))
            legend_layout.addSpacing(12)

        legend_layout.addStretch()
        piano_layout.addLayout(legend_layout)

        self.piano_widget = PianoWidget()
        self.piano_widget.setMinimumHeight(210)
        piano_layout.addWidget(self.piano_widget)

        body.addWidget(piano_group, 2)
#
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._clear_selection_panel()

    def _wire_events(self):
        self.add_button.clicked.connect(self.on_add)
        self.add_with_pin_button.clicked.connect(self.on_add_with_selected_pin)
        self.undo_button.clicked.connect(self.on_undo)
        self.delete_button.clicked.connect(self.on_delete_selected)
        self.pin_selected_button.clicked.connect(self.on_pin_selected_from_combo)
        self.unpin_selected_button.clicked.connect(self.on_unpin_selected)
        self.style_combo.currentTextChanged.connect(self.on_style_changed)

        self.chord_input.returnPressed.connect(self.on_add)
        self.chord_input.textChanged.connect(self.on_chord_input_changed)

        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self.on_table_double_clicked)

    def _clear_selection_panel(self):
        self.selected_index_label.setText("—")
        self.selected_symbol_label.setText("—")
        self.selected_bass_label.setText("—")
        self.selected_current_voicing_label.setText("—")
        self.selected_pin_status_label.setText("—")

        self.valid_voicing_combo.clear()
        self.valid_voicing_combo.addItem("(select a chord row)")
        self.valid_voicing_combo.setEnabled(False)

        self.pin_selected_button.setEnabled(False)
        self.unpin_selected_button.setEnabled(False)

        self.piano_widget.clear()

    def _set_selection_panel_from_row(self, row_index):
        if not (0 <= row_index < len(self.session.chords)):
            self._clear_selection_panel()
            return

        chord = self.session.chords[row_index]
        pinned = self.session.pins[row_index]
        row = (
            self.current_rows[row_index]
            if row_index < len(self.current_rows)
            else None
        )
        voicing = (
            self.current_voicings[row_index]
            if row_index < len(self.current_voicings)
            else None
        )

        self.selected_index_label.setText(
            str(row["index"]) if row else str(row_index + 1)
        )
        self.selected_symbol_label.setText(row["symbol"] if row else chord.symbol)
        self.selected_bass_label.setText(row["bass"] if row else "—")
        self.selected_current_voicing_label.setText(
            row["voicing"] if row else "—"
        )
        self.selected_pin_status_label.setText(pinned if pinned else "Automatic")

        labels = self.session.availableLabelsFor(row_index)

        self.valid_voicing_combo.clear()
        for label in labels:
            self.valid_voicing_combo.addItem(label)

        self.valid_voicing_combo.setEnabled(bool(labels))
        self.pin_selected_button.setEnabled(bool(labels))
        self.unpin_selected_button.setEnabled(True)

        if pinned and pinned in labels:
            self.valid_voicing_combo.setCurrentText(pinned)

        if voicing is not None:
            self.piano_widget.set_voicing(voicing)
        else:
            self.piano_widget.clear()

    def on_table_selection_changed(self):
        row = self.table.currentRow()
        if row < 0:
            self._clear_selection_panel()
            return
        self._set_selection_panel_from_row(row)

    def on_table_double_clicked(self, item):
        row = item.row()
        if not (0 <= row < len(self.session.chords)):
            return

        self.chord_input.setText(self.session.chords[row].symbol)
        self.chord_input.setFocus()

    def on_chord_input_changed(self):
        text = self.chord_input.text().strip()

        self.quick_pin_combo.clear()
        self.quick_pin_combo.addItem("(no pin)")

        if not text:
            return

        try:
            chord = parseChordSymbol(text)
            for label in availableLabels(chord):
                self.quick_pin_combo.addItem(label)
        except Exception:
            pass

    def on_add(self):
        symbol = self.chord_input.text().strip()
        if not symbol:
            return

        try:
            self.session.addChord(symbol, None)
        except Exception as e:
            QMessageBox.warning(self, "Add chord", str(e))
            return

        self.chord_input.clear()
        self.quick_pin_combo.clear()
        self.quick_pin_combo.addItem("(no pin)")
        self.request_recompute(select_row=len(self.session.chords) - 1)

    def on_add_with_selected_pin(self):
        symbol = self.chord_input.text().strip()
        if not symbol:
            return

        pin_text = self.quick_pin_combo.currentText()
        if pin_text == "(no pin)":
            pin_text = None

        try:
            self.session.addChord(symbol, pin_text)
        except Exception as e:
            QMessageBox.warning(self, "Add chord", str(e))
            return

        self.chord_input.clear()
        self.quick_pin_combo.clear()
        self.quick_pin_combo.addItem("(no pin)")
        self.request_recompute(select_row=len(self.session.chords) - 1)

    def on_undo(self):
        self.session.removeLast()
        self.request_recompute()

    def on_delete_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.session.chords):
            return

        try:
            self.session.deleteAt(row)
        except Exception as e:
            QMessageBox.warning(self, "Delete chord", str(e))
            return

        self.request_recompute()

    def on_pin_selected_from_combo(self):
        row = self.table.currentRow()
        if row < 0:
            return

        label = self.valid_voicing_combo.currentText().strip()
        if not label:
            return

        try:
            self.session.pinChord(row, label)
        except Exception as e:
            QMessageBox.warning(self, "Pin chord", str(e))
            return

        self.request_recompute(select_row=row)

    def on_unpin_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        try:
            self.session.unpinChord(row)
        except Exception as e:
            QMessageBox.warning(self, "Unpin chord", str(e))
            return

        self.request_recompute(select_row=row)

    def on_style_changed(self, style_name):
        try:
            self.session.setStyle(style_name)
        except Exception as e:
            QMessageBox.warning(self, "Style", str(e))
            return

        self.request_recompute()

    def request_recompute(self, select_row=None):
        self.pending_select_row = select_row
        self.revision += 1
        revision = self.revision
        session_copy = copy.deepcopy(self.session)
        self.last_compute_started = time.perf_counter()

        old_thread = self.active_thread
        if old_thread is not None:
            old_thread.quit()
            old_thread.wait()
            if self.active_thread is old_thread:
                self.active_thread = None
                self.active_worker = None

        thread = QThread(self)
        worker = RecomputeWorker(revision, session_copy)
        worker.moveToThread(thread)

        self.active_thread = thread
        self.active_worker = worker

        thread.started.connect(worker.run)
        worker.finished.connect(self.on_recompute_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)

        thread.finished.connect(
            lambda finished_thread=thread: self._on_thread_finished(
                finished_thread
            )
        )
        thread.finished.connect(thread.deleteLater)

        self.status.showMessage("Recomputing...")
        thread.start()

    def _on_thread_finished(self, thread):
        # Ignore cleanup signals from an earlier recompute thread.
        if self.active_thread is thread:
            self.active_thread = None
            self.active_worker = None

    def on_recompute_finished(self, revision, rows, voicings, error):
        if revision != self.revision:
            return

        if error:
            self.status.showMessage(f"Error: {error}", 5000)
            return

        self.current_rows = rows or []
        self.current_voicings = voicings or []

        previous_row = self.table.currentRow()
        self.populate_table(self.current_rows)

        row_to_select = self.pending_select_row
        if row_to_select is None:
            row_to_select = previous_row

        if row_to_select is not None and 0 <= row_to_select < len(self.current_rows):
            self.table.selectRow(row_to_select)
            self._set_selection_panel_from_row(row_to_select)
        else:
            self._clear_selection_panel()

        if self.last_compute_started is not None:
            elapsed_ms = (time.perf_counter() - self.last_compute_started) * 1000
            self.status.showMessage(f"Ready · recomputed in {elapsed_ms:.1f} ms")
        else:
            self.status.showMessage("Ready")

    def populate_table(self, rows):
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                str(row["index"]),
                row["symbol"],
                row["bass"],
                row["voicing"],
                row["notes"],
                "Yes" if row["pinned"] else "",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_index, column, item)