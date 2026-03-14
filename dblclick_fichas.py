import pyautogui, cv2
pyautogui.FAILSAFE = False

screen_img = pyautogui.screenshot()
screen_img.save(r'C:\Users\PC\Downloads\lobby2.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\lobby2.png')
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')
text_crop = ref[248:272, 100:230]

result = cv2.matchTemplate(screen, text_crop, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
h, w = text_crop.shape[:2]
cx = max_loc[0] + w // 2
cy = max_loc[1] + h // 2
print(f"FichasNet at ({cx}, {cy}), confidence={max_val:.3f}")

# Try double click
pyautogui.doubleClick(cx, cy)
print("DOUBLE CLICKED!")
