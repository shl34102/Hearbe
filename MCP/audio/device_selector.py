"""
Audio device selector

GUI selection of input (microphone) and output (speaker) devices.
Also persists the most recently selected devices.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
import tkinter as tk

try:
    import pyaudio
except ImportError:
    pyaudio = None

logger = logging.getLogger(__name__)

_PREFS_FILE = Path(__file__).resolve().parent.parent / "audio_devices.json"


def _coerce_int_or_none(value) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_device_prefs() -> Tuple[Optional[int], Optional[int], bool]:
    """Load saved device indices.

    Returns:
        (input_device_index, output_device_index, found)
    """
    if not _PREFS_FILE.exists():
        return None, None, False

    try:
        data = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Failed to read device prefs: {e}")
        return None, None, False

    input_index = _coerce_int_or_none(data.get("input_device_index"))
    output_index = _coerce_int_or_none(data.get("output_device_index"))
    return input_index, output_index, True


def save_device_prefs(input_index: Optional[int], output_index: Optional[int]) -> None:
    """Save device indices to disk."""
    data = {
        "input_device_index": input_index,
        "output_device_index": output_index
    }
    try:
        _PREFS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"Failed to save device prefs: {e}")


def validate_device_indices(
    input_index: Optional[int],
    output_index: Optional[int]
) -> Tuple[Optional[int], Optional[int]]:
    """Validate device indices against current system devices."""
    if pyaudio is None:
        return None, None

    audio = pyaudio.PyAudio()
    try:
        input_index = _validate_input_index(audio, input_index)
        output_index = _validate_output_index(audio, output_index)
    finally:
        audio.terminate()

    return input_index, output_index


def _validate_input_index(audio: Any, index: Optional[int]) -> Optional[int]:
    if index is None:
        return None
    try:
        device_info = audio.get_device_info_by_host_api_device_index(0, index)
    except Exception:
        logger.warning(f"Invalid input device index {index}; using default")
        return None
    if device_info.get("maxInputChannels", 0) <= 0:
        logger.warning(
            f"Input device index {index} has no input channels; using default"
        )
        return None
    return index


def _validate_output_index(audio: Any, index: Optional[int]) -> Optional[int]:
    if index is None:
        return None
    try:
        device_info = audio.get_device_info_by_host_api_device_index(0, index)
    except Exception:
        logger.warning(f"Invalid output device index {index}; using default")
        return None
    if device_info.get("maxOutputChannels", 0) <= 0:
        logger.warning(
            f"Output device index {index} has no output channels; using default"
        )
        return None
    return index


class DeviceSelectorDialog:
    """Tkinter dialog for selecting audio input/output devices."""

    def __init__(
        self,
        master: tk.Tk,
        default_input_index: Optional[int] = None,
        default_output_index: Optional[int] = None
    ):
        if pyaudio is None:
            raise ImportError("pyaudio not installed. Run: pip install pyaudio")

        self.master = master
        self.audio = pyaudio.PyAudio()
        self.devices = self._list_devices()
        self.input_candidates = self._get_input_candidates()
        self.output_candidates = self._get_output_candidates()

        self.default_input_index = default_input_index
        self.default_output_index = default_output_index

        self.input_map: List[Optional[int]] = []
        self.output_map: List[Optional[int]] = []
        self.result: Tuple[Optional[int], Optional[int]] = (None, None)
        self.cancelled = True

        self.top = tk.Toplevel(master)
        self.top.title("??? ?? ??")
        self.top.configure(bg="#2C3E50")
        self.top.attributes("-topmost", True)
        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build_ui()

    def _list_devices(self) -> List[Dict]:
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get("deviceCount")
        devices = []
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            devices.append(device_info)
        return devices

    def _get_input_candidates(self) -> List[int]:
        return [
            i for i, d in enumerate(self.devices)
            if d.get("maxInputChannels", 0) > 0
        ]

    def _get_output_candidates(self) -> List[int]:
        return [
            i for i, d in enumerate(self.devices)
            if d.get("maxOutputChannels", 0) > 0
        ]

    def _build_ui(self):
        body = tk.Frame(self.top, bg="#2C3E50", padx=12, pady=12)
        body.grid(row=0, column=0, sticky="nsew")

        self.top.grid_rowconfigure(0, weight=1)
        self.top.grid_columnconfigure(0, weight=1)

        mic_frame = tk.Frame(body, bg="#2C3E50")
        spk_frame = tk.Frame(body, bg="#2C3E50")
        mic_frame.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        spk_frame.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")

        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        mic_label = tk.Label(
            mic_frame,
            text="??? ??",
            font=("Segoe UI", 11, "bold"),
            fg="#ECF0F1",
            bg="#2C3E50"
        )
        mic_label.pack(anchor="w")

        spk_label = tk.Label(
            spk_frame,
            text="??? ??",
            font=("Segoe UI", 11, "bold"),
            fg="#ECF0F1",
            bg="#2C3E50"
        )
        spk_label.pack(anchor="w")

        self.input_list = self._build_listbox(mic_frame)
        self.output_list = self._build_listbox(spk_frame)

        self._populate_list(
            self.input_list,
            self.input_candidates,
            self.input_map,
            default_index=self.default_input_index
        )
        self._populate_list(
            self.output_list,
            self.output_candidates,
            self.output_map,
            default_index=self.default_output_index
        )

        if not self.input_candidates:
            self._show_empty(mic_frame, "?? ??? ???? ????")
        if not self.output_candidates:
            self._show_empty(spk_frame, "?? ??? ???? ????")

        btn_frame = tk.Frame(body, bg="#2C3E50")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(8, 0))

        ok_btn = tk.Button(
            btn_frame,
            text="??",
            width=10,
            command=self._on_ok
        )
        cancel_btn = tk.Button(
            btn_frame,
            text="??",
            width=10,
            command=self._on_cancel
        )
        ok_btn.pack(side=tk.LEFT, padx=6)
        cancel_btn.pack(side=tk.LEFT, padx=6)

        self.top.update_idletasks()
        self._center_on_screen()

    def _build_listbox(self, parent: tk.Frame) -> tk.Listbox:
        list_frame = tk.Frame(parent, bg="#2C3E50")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        listbox = tk.Listbox(
            list_frame,
            height=8,
            width=38,
            exportselection=False
        )
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)

        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return listbox

    def _populate_list(
        self,
        listbox: tk.Listbox,
        candidates: List[int],
        mapping: List[Optional[int]],
        default_index: Optional[int] = None
    ):
        listbox.insert(tk.END, "[??] ??? ?? ??")
        mapping.append(None)

        select_pos = 0 if default_index is None else None

        for device_index in candidates:
            name = self.devices[device_index].get("name", "unknown")
            listbox.insert(tk.END, f"[{device_index}] {name}")
            mapping.append(device_index)
            if default_index == device_index:
                select_pos = listbox.size() - 1

        if select_pos is not None:
            listbox.selection_set(select_pos)
            listbox.see(select_pos)

    def _show_empty(self, parent: tk.Frame, message: str):
        label = tk.Label(
            parent,
            text=message,
            font=("Segoe UI", 9),
            fg="#BDC3C7",
            bg="#2C3E50"
        )
        label.pack(anchor="w", pady=(6, 0))

    def _center_on_screen(self):
        self.top.update_idletasks()
        width = self.top.winfo_width()
        height = self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (width // 2)
        y = (self.top.winfo_screenheight() // 2) - (height // 2)
        self.top.geometry(f"{width}x{height}+{x}+{y}")

    def _on_ok(self):
        input_index = None
        output_index = None

        if self.input_list is not None:
            selection = self.input_list.curselection()
            if selection:
                input_index = self.input_map[selection[0]]

        if self.output_list is not None:
            selection = self.output_list.curselection()
            if selection:
                output_index = self.output_map[selection[0]]

        self.cancelled = False
        self.result = (input_index, output_index)
        self._close()

    def _on_cancel(self):
        self.cancelled = True
        self.result = (None, None)
        self._close()

    def _close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
        except Exception:
            pass
        if self.audio is not None:
            self.audio.terminate()
            self.audio = None

    def show_modal(self) -> Tuple[Optional[int], Optional[int], bool]:
        self.top.transient(self.master)
        self.top.grab_set()
        self.top.focus_force()
        self.top.wait_window()
        return self.result[0], self.result[1], self.cancelled
