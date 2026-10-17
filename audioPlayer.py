#!/usr/bin/env python3
"""Simple synthesized chord playback for jazzChordTool."""

import math
import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices


class TonePlayer(QObject):
    playingChanged = Signal(bool)
    playbackError = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)

        self._sink = None
        self._buffer = None
        self._playing = False

    def play_preview(self, pitches, duration_ms=1500):
        self.stop()
        self._start_chord(pitches, duration_ms)
        self._set_playing(True)
        self._timer.start(duration_ms)

    def play_progression(self, pitch_sets, tempo):
        if not pitch_sets:
            raise ValueError("Add at least one chord before playing the progression.")
        if not 40 <= tempo <= 240:
            raise ValueError("Tempo must be between 40 and 240 BPM.")

        self.stop()
        chord_duration_ms = round(120000 / tempo)
        device, audio_format = self._get_output_format()
        audio_data = bytearray()
        for pitches in pitch_sets:
            audio_data.extend(
                self._synthesize(pitches, chord_duration_ms, audio_format)
            )

        self._start_audio_data(bytes(audio_data), device, audio_format)
        self._set_playing(True)
        self._timer.start(chord_duration_ms * len(pitch_sets))

    def stop(self):
        self._timer.stop()
        self._stop_sink()
        self._set_playing(False)

    def _set_playing(self, playing):
        if self._playing != playing:
            self._playing = playing
            self.playingChanged.emit(playing)

    def _on_timer(self):
        self._finish()

    def _finish(self):
        self._timer.stop()
        self._stop_sink()
        self._set_playing(False)

    def _start_chord(self, pitches, duration_ms):
        if not pitches:
            raise ValueError("The selected voicing has no pitches to play.")
        if duration_ms <= 0:
            raise ValueError("Playback duration must be positive.")

        device, audio_format = self._get_output_format()
        data = self._synthesize(pitches, duration_ms, audio_format)
        self._start_audio_data(data, device, audio_format)

    @staticmethod
    def _get_output_format():
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            raise RuntimeError("No audio output device is available.")

        audio_format = device.preferredFormat()
        if not device.isFormatSupported(audio_format):
            raise RuntimeError(
                "The default audio output does not support its preferred format."
            )
        return device, audio_format

    def _start_audio_data(self, data, device, audio_format):
        self._buffer = QBuffer(self)
        self._buffer.setData(QByteArray(data))
        if not self._buffer.open(QBuffer.OpenModeFlag.ReadOnly):
            self._buffer.deleteLater()
            self._buffer = None
            raise RuntimeError("Could not prepare audio data for playback.")

        sink = QAudioSink(device, audio_format, self)
        self._sink = sink
        sink.stateChanged.connect(
            lambda state, active_sink=sink: self._on_sink_state_changed(
                active_sink, state
            )
        )
        sink.setVolume(0.65)
        sink.start(self._buffer)
        error = sink.error()
        if error.value != QAudio.Error.NoError.value:
            self._stop_sink()
            raise RuntimeError(f"Could not start audio playback: {error}.")

    def _on_sink_state_changed(self, sink, state):
        del state
        if (
            sink is not self._sink
            or sink.error().value == QAudio.Error.NoError.value
        ):
            return

        QTimer.singleShot(
            0,
            lambda failed_sink=sink: self._report_sink_error(failed_sink),
        )

    def _report_sink_error(self, sink):
        if (
            sink is not self._sink
            or sink.error().value == QAudio.Error.NoError.value
        ):
            return

        error = sink.error()
        self._finish()
        self.playbackError.emit(f"Audio output failed during playback: {error}.")

    @staticmethod
    def _synthesize(pitches, duration_ms, audio_format):
        if not pitches:
            raise ValueError("The selected voicing has no pitches to play.")
        if duration_ms <= 0:
            raise ValueError("Playback duration must be positive.")

        sample_rate = audio_format.sampleRate()
        channels = audio_format.channelCount()
        if sample_rate <= 0 or channels <= 0:
            raise RuntimeError("The audio output format is invalid.")

        sample_format = audio_format.sampleFormat()
        frames = round(sample_rate * duration_ms / 1000)
        frequencies = [
            440.0 * 2 ** ((pitch - 69) / 12)
            for pitch in pitches
        ]
        peak = 0.65 / len(frequencies)
        sample_bytes = audio_format.bytesPerSample()
        output = bytearray(frames * channels * sample_bytes)
        byte_order = "<" if sys.byteorder == "little" else ">"

        if sample_format == QAudioFormat.SampleFormat.Float:
            pack_code, scale, offset = "f", 1.0, 0.0
        elif sample_format == QAudioFormat.SampleFormat.Int16:
            pack_code, scale, offset = "h", 32767.0, 0.0
        elif sample_format == QAudioFormat.SampleFormat.Int32:
            pack_code, scale, offset = "i", 2147483647.0, 0.0
        elif sample_format == QAudioFormat.SampleFormat.UInt8:
            pack_code, scale, offset = "B", 127.0, 128.0
        else:
            raise RuntimeError(
                f"Unsupported audio sample format: {sample_format}."
            )

        pack_into = struct.pack_into
        pack_pattern = byte_order + pack_code
        attack_frames = max(1, round(sample_rate * 0.015))
        release_frames = max(1, round(sample_rate * 0.12))

        for frame in range(frames):
            envelope = min(
                1.0,
                frame / attack_frames,
                (frames - frame - 1) / release_frames,
            )
            sample = sum(
                math.sin(2 * math.pi * frequency * frame / sample_rate)
                for frequency in frequencies
            )
            value = max(-1.0, min(1.0, sample * peak * max(0.0, envelope)))
            packed_value = value * scale + offset
            for channel in range(channels):
                pack_into(
                    pack_pattern,
                    output,
                    (frame * channels + channel) * sample_bytes,
                    round(packed_value) if pack_code != "f" else packed_value,
                )

        return bytes(output)

    def _stop_sink(self):
        sink, self._sink = self._sink, None
        buffer, self._buffer = self._buffer, None
        if sink is not None:
            sink.stop()
            sink.deleteLater()
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()
