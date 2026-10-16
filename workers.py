#!/usr/bin/env python3
"""
Module Name: workers.py
Description: Background workers for jazzChordTool GUI
Author: Carson Towns
"""

from PySide6.QtCore import QObject, Signal, Slot


class RecomputeWorker(QObject):
    finished = Signal(int, list, str)

    def __init__(self, revision, session_copy):
        super().__init__()
        self.revision = revision
        self.session_copy = session_copy

    @Slot()
    def run(self):
        try:
            rows = self.session_copy.render_rows()
            self.finished.emit(self.revision, rows, "")
        except Exception as e:
            self.finished.emit(self.revision, [], str(e))
