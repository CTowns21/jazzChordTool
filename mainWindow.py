#!/usr/bin/env python3
"""
Module Name: mainWindow.py
Description: Main window for jazzChordTool GUI
Author: Carson Towns
"""

import copy
import json
import time

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audioPlayer import TonePlayer
from pianoWidget import PianoWidget
from sessionModel import Session
from voicingEngine import STYLES, pinnedVoicings, transitionCost, voicingCost
from workers import RecomputeWorker


SESSION_FORMAT = "jazz-chord-voicer"
SESSION_VERSION = 1


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jazz Chord Voicer")
        self.resize(1180, 720)

        self.session = Session()
        self.audio_player = TonePlayer(self)
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

        self.import_button = QPushButton("Load...")
        top.addWidget(self.import_button)

        self.export_button = QPushButton("Save...")
        top.addWidget(self.export_button)

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
        top_row.addWidget(self.table, 3)

        self.selection_group = QGroupBox("Voicing Controls")
        top_row.addWidget(self.selection_group, 1)

        controls_layout = QVBoxLayout(self.selection_group)

        controls_layout.addWidget(QLabel("Preview a voicing (does not pin):"))
        self.valid_voicing_combo = QComboBox()
        controls_layout.addWidget(self.valid_voicing_combo)

        self.pin_selected_button = QPushButton("Pin Previewed Voicing")
        controls_layout.addWidget(self.pin_selected_button)

        self.unpin_selected_button = QPushButton("Unpin")
        controls_layout.addWidget(self.unpin_selected_button)

        controls_layout.addStretch(1)

        piano_group = QGroupBox("Voicing on keyboard")
        piano_layout = QVBoxLayout(piano_group)

        legend_layout = QHBoxLayout()
        self.show_previous_chord_checkbox = QCheckBox("Show previous chord")
        self.show_previous_chord_checkbox.setChecked(True)
        legend_layout.addWidget(self.show_previous_chord_checkbox)
        legend_layout.addSpacing(12)

        legend_items = (
            ("#B8B8B8", "Previous chord"),
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

        playback_layout = QHBoxLayout()
        self.play_preview_button = QPushButton("Play Preview")
        self.play_progression_button = QPushButton("Play Progression")
        self.stop_playback_button = QPushButton("Stop")
        self.stop_playback_button.setEnabled(False)
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(40, 240)
        self.tempo_spin.setValue(100)
        self.tempo_spin.setSuffix(" BPM")
        self.tempo_spin.setToolTip("Tempo for progression playback")
        playback_layout.addWidget(self.play_preview_button)
        playback_layout.addWidget(self.play_progression_button)
        playback_layout.addWidget(self.stop_playback_button)
        playback_layout.addStretch(1)
        playback_layout.addWidget(QLabel("Tempo:"))
        playback_layout.addWidget(self.tempo_spin)
        piano_layout.addLayout(playback_layout)

        body.addWidget(piano_group, 2)
#
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._clear_selection_panel()

    def _wire_events(self):
        self.add_button.clicked.connect(self.on_add)
        self.undo_button.clicked.connect(self.on_undo)
        self.delete_button.clicked.connect(self.on_delete_selected)
        self.import_button.clicked.connect(self.on_import)
        self.export_button.clicked.connect(self.on_export)
        self.pin_selected_button.clicked.connect(self.on_pin_selected_from_combo)
        self.unpin_selected_button.clicked.connect(self.on_unpin_selected)
        self.valid_voicing_combo.currentTextChanged.connect(
            self.on_preview_voicing_changed
        )
        self.play_preview_button.clicked.connect(self.on_play_preview)
        self.play_progression_button.clicked.connect(self.on_play_progression)
        self.stop_playback_button.clicked.connect(self.on_stop_playback)
        self.audio_player.playingChanged.connect(self.on_playing_changed)
        self.audio_player.playbackError.connect(self.on_playback_error)
        self.audio_player.progressionChordChanged.connect(
            self.on_progression_chord_changed
        )
        self.show_previous_chord_checkbox.toggled.connect(
            self.on_show_previous_chord_toggled
        )
        self.style_combo.currentTextChanged.connect(self.on_style_changed)

        self.chord_input.returnPressed.connect(self.on_add)

        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self.on_table_double_clicked)

    def _clear_selection_panel(self):
        self.valid_voicing_combo.clear()
        self.valid_voicing_combo.addItem("(select a chord row)")
        self.valid_voicing_combo.setEnabled(False)

        self.pin_selected_button.setEnabled(False)
        self.unpin_selected_button.setEnabled(False)
        self.play_preview_button.setEnabled(False)

        self.piano_widget.clear()

    def _set_selection_panel_from_row(self, row_index):
        if not (0 <= row_index < len(self.session.chords)):
            self._clear_selection_panel()
            return

        pinned = self.session.pins[row_index]
        voicing = (
            self.current_voicings[row_index]
            if row_index < len(self.current_voicings)
            else None
        )

        labels = self.session.availableLabelsFor(row_index)

        previous_block_state = self.valid_voicing_combo.blockSignals(True)
        self.valid_voicing_combo.clear()
        for label in labels:
            self.valid_voicing_combo.addItem(label)

        self.valid_voicing_combo.setEnabled(bool(labels))
        self.pin_selected_button.setEnabled(bool(labels))
        self.unpin_selected_button.setEnabled(True)
        self.play_preview_button.setEnabled(bool(labels))

        selected_label = pinned
        if voicing is not None and voicing.label in labels:
            selected_label = voicing.label
        if selected_label in labels:
            self.valid_voicing_combo.setCurrentText(selected_label)
        self.valid_voicing_combo.blockSignals(previous_block_state)

        self.on_preview_voicing_changed(self.valid_voicing_combo.currentText())

    def on_preview_voicing_changed(self, label):
        row_index = self.table.currentRow()
        if not (0 <= row_index < len(self.session.chords)):
            self.piano_widget.clear()
            return

        voicings = pinnedVoicings(
            self.session.chords[row_index],
            label,
            STYLES[self.session.styleName],
        )
        if not voicings:
            self.piano_widget.clear()
            self.status.showMessage(
                f"Can't preview voicing: {label}", 5000
            )
            return

        previous_voicing = (
            self.current_voicings[row_index - 1]
            if row_index > 0 and row_index - 1 < len(self.current_voicings)
            else None
        )
        preview_voicing = min(
            voicings,
            key=lambda candidate: (
                voicingCost(candidate)
                + (
                    transitionCost(previous_voicing, candidate)
                    if previous_voicing is not None
                    else 0
                )
            ),
        )
        previous_overlay = (
            previous_voicing
            if self.show_previous_chord_checkbox.isChecked()
            else None
        )
        self.piano_widget.set_voicing(preview_voicing, previous_overlay)

    def on_play_preview(self):
        pitches = [note["midi"] for note in self.piano_widget.notes]
        try:
            self.audio_player.play_preview(pitches)
        except (RuntimeError, ValueError) as exc:
            self.on_playback_error(str(exc))
            return
        self.status.showMessage("Playing selected voicing preview")

    def on_play_progression(self):
        if not self.current_voicings:
            self.status.showMessage("Add chords before playing the progression.", 5000)
            return

        self.status.showMessage(
            f"Playing progression at {self.tempo_spin.value()} BPM"
        )
        try:
            self.audio_player.play_progression(
                [voicing.pitches for voicing in self.current_voicings],
                self.tempo_spin.value(),
            )
        except (RuntimeError, ValueError) as exc:
            self.on_playback_error(str(exc))

    def on_stop_playback(self):
        self.audio_player.stop()
        self.status.showMessage("Playback stopped", 3000)

    def on_playing_changed(self, playing):
        self.stop_playback_button.setEnabled(playing)
        self.play_preview_button.setEnabled(
            playing or 0 <= self.table.currentRow() < len(self.session.chords)
        )
        self.play_progression_button.setEnabled(
            playing or bool(self.current_voicings)
        )
        if not playing:
            self.status.showMessage("Playback finished", 3000)

    def on_progression_chord_changed(self, row):
        if not (0 <= row < len(self.current_voicings)):
            return

        self.table.selectRow(row)
        previous_voicing = self.current_voicings[row - 1] if row > 0 else None
        previous_overlay = (
            previous_voicing
            if self.show_previous_chord_checkbox.isChecked()
            else None
        )
        self.piano_widget.set_voicing(
            self.current_voicings[row],
            previous_overlay,
        )
        self.status.showMessage(
            f"Playing chord {row + 1}/{len(self.current_voicings)}: "
            f"{self.session.chords[row].symbol}"
        )

    def on_playback_error(self, message):
        self.status.showMessage(f"Audio playback error: {message}", 8000)
        QMessageBox.warning(self, "Audio playback", message)

    def on_show_previous_chord_toggled(self, checked):
        del checked
        self.on_preview_voicing_changed(self.valid_voicing_combo.currentText())

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

    def on_export(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Chord Progression",
            "chord-progression.json",
            "Chord progression (*.json)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path += ".json"

        data = {
            "format": SESSION_FORMAT,
            "version": SESSION_VERSION,
            "style": self.session.styleName,
            "chords": [
                {"symbol": chord.symbol, "pin": pin}
                for chord, pin in zip(self.session.chords, self.session.pins)
            ],
        }

        try:
            with open(file_path, "w", encoding="utf-8") as session_file:
                json.dump(data, session_file, indent=2, ensure_ascii=False)
                session_file.write("\n")
        except OSError as exc:
            QMessageBox.warning(self, "Save chord progression", str(exc))
            return

        self.status.showMessage(f"Saved chord progression to {file_path}", 5000)

    def on_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Chord Progression",
            "",
            "Chord progression (*.json)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as session_file:
                data = json.load(session_file)
            imported_session = self._session_from_data(data)
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(self, "Load chord progression", str(exc))
            return

        if self.session.chords:
            answer = QMessageBox.question(
                self,
                "Replace current progression?",
                (
                    f"Load {len(imported_session.chords)} chord(s) from "
                    f"{file_path} and replace the current progression?"
                ),
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer != QMessageBox.Yes:
                return

        self.session = imported_session
        previous_block_state = self.style_combo.blockSignals(True)
        self.style_combo.setCurrentText(imported_session.styleName)
        self.style_combo.blockSignals(previous_block_state)
        self.request_recompute(
            select_row=0 if imported_session.chords else None
        )

    @staticmethod
    def _session_from_data(data):
        if not isinstance(data, dict):
            raise ValueError("The file must contain a JSON object.")
        if data.get("format") != SESSION_FORMAT:
            raise ValueError("This is not a Jazz Chord Voicer progression file.")
        if (
            type(data.get("version")) is not int
            or data["version"] != SESSION_VERSION
        ):
            raise ValueError(
                f"Unsupported progression file version: {data.get('version')!r}"
            )
        if not isinstance(data.get("style"), str):
            raise ValueError("The progression file must include a style.")
        if not isinstance(data.get("chords"), list):
            raise ValueError("The progression file must include a chords list.")

        imported_session = Session()
        imported_session.setStyle(data["style"])

        for index, chord_data in enumerate(data["chords"], start=1):
            if not isinstance(chord_data, dict):
                raise ValueError(f"Chord {index} must be a JSON object.")
            symbol = chord_data.get("symbol")
            pin = chord_data.get("pin")
            if not isinstance(symbol, str):
                raise ValueError(f"Chord {index} must include a symbol.")
            if pin is not None and not isinstance(pin, str):
                raise ValueError(f"The pin for chord {index} must be text or null.")
            try:
                imported_session.addChord(symbol, pin)
            except ValueError as exc:
                raise ValueError(f"Invalid chord {index}: {exc}") from exc

        return imported_session

    def request_recompute(self, select_row=None):
        self.audio_player.stop()
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
        self.play_progression_button.setEnabled(bool(self.current_voicings))

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

    def closeEvent(self, event):
        self.audio_player.stop()
        super().closeEvent(event)