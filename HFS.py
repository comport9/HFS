"""
HFS — HotS Favourites Selector
Auto-selects your favourited talents in Heroes of the Storm via on-screen image
matching. Press Start, then play; favourited talents are picked for you.
"""

import sys
import time
import ctypes
import threading

from tkinter import *
from tkinter import font as tkFont

import cv2
import numpy as np
import pyautogui
import win32gui
from skimage.metrics import structural_similarity

FAVOURITE = 'heart.png'
NEWTALENT = 'newtalent.png'
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
BACKGROUND_COLOUR = '#1c2833'
BUTTON_START = '#2f79ad'
START_ACTIVE = '#3b97d9'
BUTTON_STOP = '#ad402f'
STOP_ACTIVE = '#d9503b'

GAME_TITLE = 'Heroes of the Storm'

# Win32 mouse event flags.
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# x, y, w, h - Heart graphic (one per talent row).
HEART_LOCS = [(38, 362, 17, 17), (38, 439, 17, 17), (38, 516, 17, 17),
              (38, 593, 17, 17), (38, 671, 17, 17), (38, 748, 17, 17)]
# x, y, w, h - New talent indicator.
CHECK_TALENT = (75, 1032, 80, 15)

# HSV range to cut from images.
SENSITIVITY = 60
CHECK_TALENT_RANGE = [[0, 0, 255 - SENSITIVITY], [255, SENSITIVITY, 255]]

# Match thresholds (SSIM, 1.0 == a perfect match).
HEART_THRESHOLD = 0.90
TALENT_THRESHOLD = 0.85

# x, y - first talent row; rows are spaced TALENT_ROW_SPACING apart (pre-scaling).
TALENT_SELECT = (200, 390)
TALENT_ROW_SPACING = 77

# x, y - the button that opens the talent panel.
TALENT_OPEN = (110, 975)


class Window:
    def __init__(self):
        self.window = Tk()
        self.window.title('HotS Favourites Selector')
        self.window.geometry('300x110')
        self.window.configure(background=BACKGROUND_COLOUR)
        self.window.iconbitmap('HFS.ico')
        self.window.resizable(False, False)
        self.window.protocol('WM_DELETE_WINDOW', self.on_close)

        self.screen_width = self.window.winfo_screenwidth()
        self.screen_height = self.window.winfo_screenheight()
        self.scaleX = self.screen_width / DEFAULT_WIDTH
        self.scaleY = self.screen_height / DEFAULT_HEIGHT
        self.font = tkFont.Font(family='Tahoma', size=20, weight='bold')

        # Load + pre-scale the template images once (not on every frame).
        self.favourite, self.fav_size = self._load_template(FAVOURITE)
        newtalent, self.talent_size = self._load_template(NEWTALENT)
        self.newtalent = self.clean_image(newtalent)

        self.watcher_status = False
        self.thread = None
        self.button = Button(self.window, text='Start', width=16, height=2,
                             font=self.font, bg=BUTTON_START, fg='white',
                             activebackground=START_ACTIVE, activeforeground='white',
                             command=self.on_start)
        self.button.place(relx=0.5, rely=0.5, anchor=CENTER)

        self.window.mainloop()

    # ── Template loading ─────────────────────────────────────────

    def _load_template(self, path):
        """Read an image, scale it to the current resolution, return (img, (w, h))."""
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(f"Could not load required image: {path}")
        h, w = img.shape[:2]
        w, h = self.scale_XY(w, h)
        img = cv2.resize(img, (w, h))
        return img, (w, h)

    # ── Start / stop (all UI changes happen on the main thread) ──

    def on_start(self):
        if self.watcher_status:
            return
        self.watcher_status = True
        self.window.title('HFS is running...')
        self.button.config(text='Stop', bg=BUTTON_STOP,
                           activebackground=STOP_ACTIVE, command=self.on_stop)
        self.thread = threading.Thread(target=self.start_watcher, daemon=True)
        self.thread.start()

    def on_stop(self):
        self.watcher_status = False
        self.window.title('HFS has stopped...')
        self.button.config(text='Start', bg=BUTTON_START,
                           activebackground=START_ACTIVE, command=self.on_start)

    def on_close(self):
        self.watcher_status = False
        self.window.destroy()

    # ── Window focus ─────────────────────────────────────────────

    def check_focus(self):
        """Title of the currently focused window."""
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())

    # ── Main watch loop (runs on the worker thread) ──────────────

    def start_watcher(self):
        while self.watcher_status:
            if self.check_focus() != GAME_TITLE:
                time.sleep(2)
                continue

            time.sleep(1)
            image = self.get_screenshot()
            loc = self.check_for_hearts(image)
            new = self.check_for_new_talent(image)

            if new and loc is not None:
                x, y = self.mouse_position()
                self.select_talent(loc)
                self.mouse_move(x, y)
            elif new and loc is None:
                # Talent panel may be closed — open it, then look again.
                x, y = self.mouse_position()
                self.open_talent()
                self.mouse_move(x, y)
                time.sleep(.2)
                image = self.get_screenshot()
                loc = self.check_for_hearts(image)
                if loc is not None:
                    x, y = self.mouse_position()
                    self.select_talent(loc)
                    self.mouse_move(x, y)

    # ── Mouse helpers ────────────────────────────────────────────

    def mouse_move(self, x, y):
        ctypes.windll.user32.SetCursorPos(x, y)

    def mouse_click(self):
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def mouse_position(self):
        return win32gui.GetCursorPos()

    # ── Scaling helpers ──────────────────────────────────────────

    def scaled_X(self, num):
        return round(num * self.scaleX)

    def scaled_Y(self, num):
        return round(num * self.scaleY)

    def scale_XY(self, x, y):
        return self.scaled_X(x), self.scaled_Y(y)

    # ── Image matching ───────────────────────────────────────────

    def compare_images(self, img1, img2):
        """SSIM similarity (1.0 == identical), robust to skimage version + bad crops."""
        if img1 is None or img2 is None or img1.shape != img2.shape:
            return 0.0
        try:
            return structural_similarity(img1, img2, channel_axis=-1, data_range=255)
        except TypeError:
            # scikit-image < 0.19 used `multichannel` instead of `channel_axis`.
            return structural_similarity(img1, img2, multichannel=True, data_range=255)
        except ValueError:
            # e.g. a crop smaller than the SSIM window.
            return 0.0

    def get_screenshot(self):
        image = pyautogui.screenshot()
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def check_for_hearts(self, image):
        """Return the index of the talent row showing the favourite heart, or None."""
        w, h = self.fav_size
        for count, heart in enumerate(HEART_LOCS):
            x, y, _, _ = heart
            x, y = self.scale_XY(x, y)
            crop = image[y:y + h, x:x + w]
            if self.compare_images(crop, self.favourite) > HEART_THRESHOLD:
                return count
        return None

    def check_for_new_talent(self, image):
        """True if the 'new talent available' indicator is on screen."""
        w, h = self.talent_size
        x, y, _, _ = CHECK_TALENT
        x, y = self.scale_XY(x, y)
        crop = self.clean_image(image[y:y + h, x:x + w])
        return self.compare_images(crop, self.newtalent) > TALENT_THRESHOLD

    def clean_image(self, image):
        """Mask everything except near-full whites (via HSV range)."""
        lower = np.array(CHECK_TALENT_RANGE[0], dtype=np.uint8)
        upper = np.array(CHECK_TALENT_RANGE[1], dtype=np.uint8)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        return cv2.bitwise_and(image, image, mask=mask)

    # ── Talent actions ───────────────────────────────────────────

    def select_talent(self, loc):
        x, y = self.scale_XY(*TALENT_SELECT)
        y += round(self.scaleY * TALENT_ROW_SPACING) * loc
        self.mouse_move(x, y)
        self.mouse_click()

    def open_talent(self):
        x, y = self.scale_XY(*TALENT_OPEN)
        self.mouse_move(x, y)
        self.mouse_click()


if __name__ == '__main__':
    Window()
    sys.exit()
