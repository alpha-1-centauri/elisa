from aicsimageio import AICSImage
import cv2
from matplotlib import pyplot as plt

path='counts/AMP4-B06A/AMP04-B06A-Scene-01-B2-B2.czi'

img = AICSImage(path)
img = img.get_image_data("YX")

scale_percent = 20 # percent of original size
width = int(img.shape[1] * scale_percent / 100)
height = int(img.shape[0] * scale_percent / 100)
dim = (width, height)

# resize image
resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

cv2.imshow('t',resized)
cv2.waitKey(0)
