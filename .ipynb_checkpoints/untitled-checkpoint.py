from aicsimageio import AICSImage
import cv2
from matplotlib import pyplot as plt

path='input/counts/AMP4-B06A/AMP04-B06A-Scene-01-B2-B2.czi'

img = AICSImage(path)
first_channel_data = img.get_image_data("YX")

cv2.imshow('t',first_channel_data)
cv2.waitKey(0)

gray = cv.cvtColor(src, cv.COLOR_BGR2GRAY)