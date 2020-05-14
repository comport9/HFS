from skimage import measure
import pyautogui
from tkinter import *
from tkinter import font as tkFont
import threading
import win32gui
import numpy as np
import ctypes
import time
import cv2

FAVOURITE = 'favourite.png'
NEWTALENT = 'newtalent.png'
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
BACKGROUND_COLOUR = '#1c2833'
BUTTON_START = '#2f79ad'
START_ACTIVE = '#3b97d9'
BUTTON_STOP = '#ad402f'
STOP_ACTIVE = '#d9503b'

# x, y, w, h - Heart graphic.
HEART_LOCS = [(38, 363, 19, 22), (38, 440, 19, 22), (38, 517, 19, 22), (38, 594, 19, 22), (38, 671, 19, 22), (38, 748, 19, 22)]
																								
# x, y, w, h - New talent indicator.
CHECK_TALENT = (75, 1032, 80, 15)

# HSV range to cut from images.
SENSITIVITY = 60
CHECK_TALENT_RANGE = [[0, 0, 255-SENSITIVITY], [255, SENSITIVITY, 255]]

# x, y - y += 77*index(HEART_LOCS)
TALENT_SELECT = (200, 390)

# x, y
TALENT_OPEN = (110, 975)

class Window():
	def __init__(self):
		self.window = Tk()	
		self.window.geometry('300x110')
		self.window.configure(background=BACKGROUND_COLOUR)
		self.window.iconbitmap("HotSLogo.ico")
		self.screen_width = self.window.winfo_screenwidth()
		self.screen_height = self.window.winfo_screenheight()
		self.scaleX = self.screen_width / DEFAULT_WIDTH
		self.scaleY = self.screen_height / DEFAULT_HEIGHT
		self.font = tkFont.Font(family='Tahoma', size=20, weight='bold')	

		self.start()

		self.window.protocol("WM_DELETE_WINDOW", self.exit)
		self.window.mainloop()

	def doNothing(self):
		print('...do nothing...')

	# Start button. Starts the Watcher.
	def start(self):
		self.watcher_status = False
		self.window.title('HFS is stopped...')
		self.startButton = Button(	self.window, 
									text='Start', 
									width=16, 
									height=2, 
									font=self.font, 
									bg=BUTTON_START, 
									fg='white',
									activebackground=START_ACTIVE,
									activeforeground='white',
									command=self.activate_watcher_thread)
		self.startButton.place(relx=0.5, rely=0.5, anchor=CENTER)

	# Stop button. Stops the Watcher.
	def stop(self):
		self.watcher_status = True
		self.window.title('HFS is running...')
		self.startButton = Button(	self.window, 
									text='Stop', 
									width=16, height=2, 
									font=self.font, 
									bg=BUTTON_STOP, 
									fg='white',
									activebackground=STOP_ACTIVE,
									activeforeground='white',
									command=self.start)
		self.startButton.place(relx=0.5, rely=0.5, anchor=CENTER)

	# Creates a thread inwhich to run the watcher.
	def activate_watcher_thread(self):
		thread = threading.Thread(target=self.start_watcher)
		thread.deamon = True
		thread.start()

	# Exits Watcher, destroys all windows.
	def exit(self):
		self.watcher_status = False
		self.window.destroy()
		self.window.quit()

	# Starts main program.
	def start_watcher(self):
		self.stop()
		while self.watcher_status == True:
			time.sleep(1)
			image = self.get_screenshot()
			loc = self.check_for_hearts(image)
			new = self.check_for_new_talent(image)
			if loc != None and new == True:
				x, y = self.mouse_position()
				self.select_talent(loc)
				self.mouse_move(x, y)
			elif loc == None and new == True:
				x, y = self.mouse_position()
				self.open_talent()
				self.mouse_move(x, y)
				time.sleep(.2)
				image = self.get_screenshot()
				loc = self.check_for_hearts(image)
				x, y = self.mouse_position()
				if loc != None:
					self.select_talent(loc)
					self.mouse_move(x, y)
		
	# Moves the mouse cursor to target location.
	def mouse_move(self, x, y):
		ctypes.windll.user32.SetCursorPos(x, y)

	# Left clicks the mouse.
	def mouse_click(self):
		ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
		ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)

	# Gets the users current cursor position
	def mouse_position(self):
		x, y = win32gui.GetCursorPos()
		return (x, y)

	# Scale number by the X scaler.
	def scaled_X(self, num):
		return round(num * self.scaleX)

	# Scale number by the Y scaler.
	def scaled_Y(self, num):
		return round(num * self.scaleY)

	# Scale by the X and Y scaler.
	def scale_XY(self, x, y):
		x = self.scaled_X(x)
		y = self.scaled_Y(y)
		return x, y

	# Compares images, returning a SSIM number. 1 is a perfect match.
	def compare_images(self, img1, img2):
		return measure.compare_ssim(img1, img2, multichannel=True)

	# Takes a screenshot and returns it.
	def get_screenshot(self):
		image = pyautogui.screenshot()
		image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
		return image

	# Checks for 'favourite.png' graphic in screenshot.
	def check_for_hearts(self, image):
		favourite = cv2.imread(FAVOURITE)
		height, width, channels = favourite.shape
		width, height = self.scale_XY(width, height)
		favourite = cv2.resize(favourite, (width, height))
		for count, heart in enumerate(HEART_LOCS):
			x, y, w, h = heart
			x, y = self.scale_XY(x, y)
			crop = image[y:y+height, x:x+width]
			comp = self.compare_images(crop, favourite)
			if comp > .60:
				return count
		return None

	# Checks if new talent available.
	def check_for_new_talent(self, image):
		talent = cv2.imread(NEWTALENT)
		height, width, channels = talent.shape
		width, height = self.scale_XY(width, height)
		talent = cv2.resize(talent, (width, height))
		x, y, w, h = CHECK_TALENT
		x, y = self.scale_XY(x, y)
		crop = image[y:y+height, x:x+width]
		talent = self.clean_image(talent)
		crop = self.clean_image(crop)
		comp = self.compare_images(crop, talent)
		if comp > .90:
			return True
		return False

	# Masks image so that only near-to-full whites remain.
	def clean_image(self, image):
		MIN, MAX = CHECK_TALENT_RANGE
		lower = np.array(MIN, dtype=np.uint8)
		upper = np.array(MAX, dtype=np.uint8)
		hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
		mask = cv2.inRange(hsv, lower, upper)
		output = cv2.bitwise_and(image, image, mask=mask)
		return output

	# Selects specified talent.
	def select_talent(self, loc):
		x, y = TALENT_SELECT
		x, y = self.scale_XY(x, y)
		y += (round(self.scaleY * 77) * loc)
		self.mouse_move(x, y)
		self.mouse_click()

	# Open talent selections.
	def open_talent(self):
		Tx, Ty = TALENT_OPEN
		Tx, Ty = self.scale_XY(Tx, Ty)
		self.mouse_move(Tx, Ty)
		self.mouse_click()

if __name__ == '__main__':
	win = Window()
