#!/usr/bin/env python3
"""SoundFont playback for jazzChordTool."""

import importlib
import os
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices


class FluidSynthUnavailableError(RuntimeError):
    """Raised when pyFluidSynth or its native library cannot be loaded."""


class TonePlayer(QObject):
    playingChanged = Signal(bool)
    playbackError = Signal(str)
    progressionChordChanged = Signal(int)

    SAMPLE_RATE = 48000
    CHANNEL = 0
    RELEASE_SECONDS = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)

        self._sink = None
        self._buffer = None
        self._playing = False
        self._synth = None
        self._soundfont_id = None
        self._soundfont_path = None
        self._preset_bank = 0
        self._preset_number = 0
        self._volume = 0.7
        self._reverb = 0.35
        self._fluidsynth_module = None
        self._progression_chord_duration_ms = 0
        self._progression_chord_count = 0
        self._progression_chord_index = 0
        self._dll_directory_handles = []
        self._dll_directory_paths = set()

    @property
    def soundfont_path(self):
        return self._soundfont_path

    @property
    def soundfont_loaded(self):
        return self._synth is not None

    def load_soundfont(self, path):
        self.stop()
        soundfont_path = Path(path)
        if not soundfont_path.is_file():
            raise ValueError(f"SoundFont file does not exist: {soundfont_path}")

        fluidsynth = self._load_fluidsynth()
        synth = fluidsynth.Synth(gain=0.2, samplerate=self.SAMPLE_RATE)
        soundfont_id = synth.sfload(str(soundfont_path))
        if soundfont_id < 0:
            synth.delete()
            raise ValueError(f"FluidSynth could not load: {soundfont_path}")

        presets = []
        for preset_number in range(128):
            name = synth.sfpreset_name(soundfont_id, 0, preset_number)
            if name:
                presets.append((0, preset_number, name))
        if not presets:
            synth.delete()
            raise ValueError(
                "The SoundFont has no presets in bank 0, so no instrument "
                "can be selected."
            )

        self._delete_synth()
        self._synth = synth
        self._soundfont_id = soundfont_id
        self._soundfont_path = str(soundfont_path)
        self._preset_bank, self._preset_number, _ = presets[0]
        self._synth.program_select(
            self.CHANNEL,
            self._soundfont_id,
            self._preset_bank,
            self._preset_number,
        )
        self._synth.set_reverb(level=self._reverb)
        return presets

    def select_preset(self, bank, preset):
        if self._synth is None or self._soundfont_id is None:
            raise RuntimeError("Load a SoundFont before selecting an instrument.")
        fluidsynth = self._load_fluidsynth()
        result = self._synth.program_select(
            self.CHANNEL, self._soundfont_id, bank, preset
        )
        if result != fluidsynth.FLUID_OK:
            raise ValueError(f"Could not select SoundFont preset {bank}:{preset}.")
        self._preset_bank = bank
        self._preset_number = preset

    def set_volume(self, volume):
        self._volume = max(0.0, min(1.0, volume))
        if self._sink is not None:
            self._sink.setVolume(self._volume)

    def set_reverb(self, level):
        self._reverb = max(0.0, min(1.0, level))
        if self._synth is not None:
            self._synth.set_reverb(level=self._reverb)

    def play_preview(self, pitches, duration_ms=1500):
        self.stop()
        self._require_synth()
        if not pitches:
            raise ValueError("The selected voicing has no pitches to play.")
        if duration_ms <= 0:
            raise ValueError("Playback duration must be positive.")

        audio_data = bytearray()
        self._note_on(pitches)
        audio_data.extend(self._render(duration_ms))
        self._note_off(pitches)
        audio_data.extend(self._render(self.RELEASE_SECONDS * 1000))
        self._start_audio_data(bytes(audio_data))
        self._set_playing(True)

    def play_progression(self, pitch_sets, tempo):
        if not pitch_sets:
            raise ValueError("Add at least one chord before playing the progression.")
        if not 40 <= tempo <= 240:
            raise ValueError("Tempo must be between 40 and 240 BPM.")

        self.stop()
        self._require_synth()
        chord_duration_ms = round(120000 / tempo)
        audio_data = bytearray()
        previous_pitches = []
        for pitches in pitch_sets:
            if not pitches:
                raise ValueError("A progression chord has no pitches to play.")
            if previous_pitches:
                self._note_off(previous_pitches)
            self._note_on(pitches)
            audio_data.extend(self._render(chord_duration_ms))
            previous_pitches = pitches

        self._note_off(previous_pitches)
        audio_data.extend(self._render(self.RELEASE_SECONDS * 1000))
        self._start_audio_data(bytes(audio_data))
        self._progression_chord_duration_ms = chord_duration_ms
        self._progression_chord_count = len(pitch_sets)
        self._progression_chord_index = 0
        self._set_playing(True)
        self.progressionChordChanged.emit(0)
        self._timer.start(chord_duration_ms)

    def stop(self):
        self._timer.stop()
        self._stop_sink()
        if self._synth is not None:
            self._synth.all_sounds_off(self.CHANNEL)
        self._reset_progression()
        self._set_playing(False)

    def close(self):
        self.stop()
        self._delete_synth()
        self._soundfont_path = None
        self._close_dll_directory_handles()

    def add_dll_directory(self, directory):
        if os.name != "nt":
            raise RuntimeError("Selecting a FluidSynth DLL folder is Windows-only.")

        dll_directory = Path(directory).expanduser().resolve()
        if not dll_directory.is_dir():
            raise ValueError(f"FluidSynth folder does not exist: {dll_directory}")

        if not any(dll_directory.glob("libfluidsynth*.dll")):
            raise ValueError(
                f"No libfluidsynth DLL was found in {dll_directory}. "
                "Choose the folder containing the FluidSynth DLL."
            )

        self._register_dll_directory(dll_directory)
        self._load_fluidsynth()

    def _load_fluidsynth(self):
        if self._fluidsynth_module is not None:
            return self._fluidsynth_module

        if os.name == "nt":
            program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            candidate_dirs = [
                Path(os.environ["FLUIDSYNTH_DLL_DIR"])
                if os.environ.get("FLUIDSYNTH_DLL_DIR")
                else None,
                Path(r"C:\tools\fluidsynth\bin"),
                program_files / "FluidSynth" / "bin",
                program_files / "VMPK",
            ]
            for directory in candidate_dirs:
                if directory is not None and directory.is_dir():
                    self._register_dll_directory(directory)

        try:
            self._fluidsynth_module = importlib.import_module("fluidsynth")
            return self._fluidsynth_module
        except (ImportError, OSError) as exc:
            raise FluidSynthUnavailableError(
                "Could not load pyFluidSynth or the FluidSynth native library. "
                "Install FluidSynth and select the folder containing its DLL."
            ) from exc

    def _register_dll_directory(self, directory):
        directory = Path(directory).resolve()
        directory_key = str(directory).casefold()
        if directory_key in self._dll_directory_paths:
            return

        self._dll_directory_handles.append(
            os.add_dll_directory(str(directory))
        )
        self._dll_directory_paths.add(directory_key)
        os.environ["PATH"] = (
            str(directory) + os.pathsep + os.environ.get("PATH", "")
        )

    def _close_dll_directory_handles(self):
        for handle in self._dll_directory_handles:
            handle.close()
        self._dll_directory_handles.clear()
        self._dll_directory_paths.clear()

    def _require_synth(self):
        if self._synth is None:
            self._load_fluidsynth()
            raise RuntimeError(
                "Load a SoundFont first. Use a compatible .sf2 or .sf3 file."
            )
        return self._synth

    def _note_on(self, pitches):
        fluidsynth = self._load_fluidsynth()
        for pitch in pitches:
            result = self._require_synth().noteon(self.CHANNEL, pitch, 90)
            if result != fluidsynth.FLUID_OK:
                raise ValueError(f"SoundFont could not play MIDI note {pitch}.")

    def _note_off(self, pitches):
        for pitch in pitches:
            self._require_synth().noteoff(self.CHANNEL, pitch)

    def _render(self, duration_ms):
        frame_count = round(self.SAMPLE_RATE * duration_ms / 1000)
        return self._require_synth().get_samples(frame_count).tobytes()

    def _get_output(self):
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            raise RuntimeError("No audio output device is available.")

        audio_format = QAudioFormat()
        audio_format.setSampleRate(self.SAMPLE_RATE)
        audio_format.setChannelCount(2)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(audio_format):
            raise RuntimeError(
                "The audio output does not support FluidSynth's 48 kHz stereo "
                "format."
            )
        return device, audio_format

    def _start_audio_data(self, data):
        device, audio_format = self._get_output()
        buffer = QBuffer(self)
        buffer.setData(QByteArray(data))
        if not buffer.open(QBuffer.OpenModeFlag.ReadOnly):
            buffer.deleteLater()
            raise RuntimeError("Could not prepare SoundFont audio for playback.")

        sink = QAudioSink(device, audio_format, self)
        self._buffer = buffer
        self._sink = sink
        sink.stateChanged.connect(
            lambda state, active_sink=sink: self._on_sink_state_changed(
                active_sink, state
            )
        )
        sink.setVolume(self._volume)
        sink.start(buffer)
        error = sink.error()
        if error.value != QAudio.Error.NoError.value:
            self._stop_sink()
            raise RuntimeError(f"Could not start audio playback: {error}.")

    def _on_sink_state_changed(self, sink, state):
        if sink is not self._sink:
            return
        if sink.error().value != QAudio.Error.NoError.value:
            QTimer.singleShot(
                0,
                lambda failed_sink=sink: self._report_sink_error(failed_sink),
            )
        elif state.value == QAudio.State.IdleState.value:
            self._finish_after_drain()

    def _report_sink_error(self, sink):
        if (
            sink is not self._sink
            or sink.error().value == QAudio.Error.NoError.value
        ):
            return
        error = sink.error()
        self._finish()
        self.playbackError.emit(f"Audio output failed during playback: {error}.")

    def _on_timer(self):
        next_index = self._progression_chord_index + 1
        if next_index < self._progression_chord_count:
            self._progression_chord_index = next_index
            self.progressionChordChanged.emit(next_index)
            self._timer.start(self._progression_chord_duration_ms)

    def _finish_after_drain(self):
        if self._progression_chord_count:
            last_index = self._progression_chord_count - 1
            if self._progression_chord_index != last_index:
                self._progression_chord_index = last_index
                self.progressionChordChanged.emit(last_index)
        self._finish()

    def _finish(self):
        self._timer.stop()
        self._stop_sink()
        self._reset_progression()
        self._set_playing(False)

    def _reset_progression(self):
        self._progression_chord_duration_ms = 0
        self._progression_chord_count = 0
        self._progression_chord_index = 0

    def _set_playing(self, playing):
        if self._playing != playing:
            self._playing = playing
            self.playingChanged.emit(playing)

    def _delete_synth(self):
        if self._synth is not None:
            self._synth.delete()
            self._synth = None
            self._soundfont_id = None

    def _stop_sink(self):
        sink, self._sink = self._sink, None
        buffer, self._buffer = self._buffer, None
        if sink is not None:
            sink.stop()
            sink.deleteLater()
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()
