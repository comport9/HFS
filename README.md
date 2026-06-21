# HFS — HotS Favourites Selector

A favourite-talent auto-selector for **Heroes of the Storm**.

Run the program, hit **Start**, and while you play, any talents you've favourited
(marked with a heart) are selected for you automatically.

## How it works

HFS watches the screen while Heroes of the Storm is the focused window. Once a
"new talent available" indicator appears, it uses on-screen image matching (SSIM)
to find which talent row carries your favourite heart icon, moves the mouse there,
clicks it, and restores your cursor to where it was.

Built for **1920 × 1080**, but it scales to other resolutions. Your in-game
resolution must match your display resolution, and you must run the game in
**Fullscreen** or **Fullscreen (Windowed)** mode.

## Files

| File | Purpose |
|------|---------|
| `HFS.py` | The program. |
| `heart.png` | The favourite-heart template image. |
| `newtalent.png` | The "new talent available" indicator template. |
| `HFS.ico` | Window icon. |

## Requirements

Python 3 plus these packages:

```bash
pip install opencv-python numpy pyautogui pywin32 scikit-image
```

(`tkinter`, `ctypes`, `threading`, `time`, and `sys` are part of the standard library.)

## Running

```bash
python HFS.py
```

## Version history

- **v2.0** — Modernized:
  - Fixed the scikit-image break (`multichannel` → `channel_axis`, with a fallback
    for older versions) so it runs on current installs again.
  - Added the missing `import sys`.
  - Thread-safe UI: Start/Stop now update widgets on the main thread only.
  - Template images are loaded once at startup instead of every frame.
  - Single Start/Stop button is reconfigured instead of stacking new widgets.
  - Graceful window-close handling and clearer errors if an image is missing.
  - Named the Win32 mouse-event flags; tidied scaling/match thresholds.
  - The original is preserved on the [`original`](https://github.com/comport9/HFS/tree/original) branch.

— Neil J. Bruce
