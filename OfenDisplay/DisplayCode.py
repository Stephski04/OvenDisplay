#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in13_V4
import time
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button
import RPi.GPIO as GPIO

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# GPIO Setup
GPIO.setwarnings(False)  # Disable GPIO warnings
GPIO.setmode(GPIO.BCM)  # Use BCM numbering for pins

# Button GPIO Pins
MODE_BUTTON_PIN = 21  # Button 1 (GPIO 21) for e-paper mode switching
LED_BUTTON_PIN = 20   # Button 2 (GPIO 20) for LED toggling
TIMER_BUTTON_PIN = 16 # Button 3 (GPIO 16) for timer control
LED_PIN = 19          # GPIO 19 for LED control

# GPIO Setup
GPIO.setup(LED_PIN, GPIO.OUT)  # Set LED pin as output
GPIO.setup(MODE_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set Button 1 (Mode) as input with pull-up resistor
GPIO.setup(LED_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set Button 2 (LED) as input with pull-up resistor
GPIO.setup(TIMER_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set Button 3 (Timer) as input with pull-up resistor

# Button State Tracking for LED
BS1 = False  # LED state tracking

# Modes List
modes = ["Umluft", "Oberhitze", "Heisluft", "Unterhitze"]
mode_index = 0  # Start with the first mode

# Timer state (in seconds)
timer_value = 20 * 60  # Set initial timer to 20 minutes (1200 seconds)
timer_running = False  # To track whether the timer is running

# Initialize Buttons
mode_button = Button(MODE_BUTTON_PIN)
led_button = Button(LED_BUTTON_PIN)
timer_button = Button(TIMER_BUTTON_PIN)

# Static Image Drawing (with Modes and Timer Area)
def create_static_image():
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)

    # Create a blank image for the static content
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    # Static text to be drawn once
    draw.text((0, 0), 'Modes', font=font15, fill=0)
    draw.text((200, 0), 'Light', font=font15, fill=0)
    draw.text((200, 80), 'temp:', font=font15, fill=0)
    draw.text((200, 100), '220', font=font15, fill=0)
    draw.text((0, 80), 'timer:', font=font15, fill=0)
    draw.text((0, 100), '20:00', font=font15, fill=0)
    draw.text((90, 100), 'Fan', font=font15, fill=0)

    # Initially draw the mode text (Mode 1)
    draw.text((20, 50), modes[mode_index], font=font24, fill=0)
    time.sleep(1)

    # Return the static image with initial mode text
    return image

# Function to update only the mode text (partial update)
def update_mode_display(epd, image):
    global mode_index
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
    
    # Copy the static image to avoid modifying it directly
    image_copy = image.copy()
    draw = ImageDraw.Draw(image_copy)

    # Clear the previous mode text area and draw the new mode
    draw.rectangle((20, 50, epd.width, 70), fill=255)  # Clear the mode area
    draw.text((20, 50), modes[mode_index], font=font24, fill=0)

    # Display the updated image with the new mode (partial update)
    epd.displayPartial(epd.getbuffer(image_copy))  # Correct method name: displayPartial

# Function to handle mode switching
def mode_button_pressed():
    global mode_index
    mode_index = (mode_index + 1) % len(modes)  # Cycle through modes
    update_mode_display(epd, static_image)

# Function to handle LED toggle and start the timer
def led_button_pressed():
    global BS1, timer_running, timer_value

    if not BS1:  # If LED is OFF, turn it ON and start/reset the timer
        GPIO.output(LED_PIN, True)
        BS1 = True
        timer_running = True  # Start the timer
        logging.info("LED turned ON and Timer started.")
    else:  # If LED is ON, turn it OFF and stop the timer
        GPIO.output(LED_PIN, False)
        BS1 = False
        timer_running = False  # Stop the timer
        logging.info("LED turned OFF and Timer stopped.")

    # Update the display with the current timer
    update_timer_display(epd, static_image)

# Timer formatting function
def format_timer(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02}:{seconds:02}"

# Function to update the timer display area (partial update)
def update_timer_display(epd, image):
    global timer_value

    # Copy the static image to avoid modifying it directly
    image_copy = image.copy()
    draw = ImageDraw.Draw(image_copy)

    # Clear the previous timer area and draw the new timer value
    draw.rectangle((0, 80, epd.width, 120), fill=255)  # Clear the timer area
    draw.text((0, 100), format_timer(timer_value), font=ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15), fill=0)

    # Perform partial update (only refresh the timer area)
    epd.displayPartial(epd.getbuffer(image_copy))

# Function to handle timer button press
def timer_button_pressed():
    global timer_value

    # Increment the timer by 60 seconds (1 minute)
    timer_value += 60

    # Reset the timer if it exceeds 20 minutes
    if timer_value > 20 * 60:
        timer_value = 0

    # Update the display with the new timer value
    update_timer_display(epd, static_image)

# Initialize the e-paper display and static content
try:
    logging.info("Starting E-paper Display with Button Control")

    epd = epd2in13_V4.EPD()
    
    # Create static image with modes and other information
    static_image = create_static_image()

    # Display the static content with initial mode
    epd.display(epd.getbuffer(static_image))

    # Button event handlers
    mode_button.when_pressed = mode_button_pressed  # Trigger on mode button press
    led_button.when_pressed = led_button_pressed    # Trigger on LED button press
    timer_button.when_pressed = timer_button_pressed  # Trigger on timer button press

    # Keep the script running and wait for button presses
    while True:
        if timer_running:
            # If the timer is running, decrement the timer every second
            time.sleep(1)
            if timer_value > 0:
                timer_value -= 1
                update_timer_display(epd, static_image)  # Update the timer on the display
            else:
                logging.info("Timer reached zero")
                timer_running = False  # Stop the timer when it reaches 0

        time.sleep(0.1)  # Just to keep the program alive and responsive to button presses

except KeyboardInterrupt:
    logging.info("Exiting program")
    epd2in13_V4.epdconfig.module_exit(cleanup=True)  # Clean up e-paper display
    GPIO.cleanup()  # Clean up GPIO settings
    exit()

