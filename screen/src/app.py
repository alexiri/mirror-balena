import RPi.GPIO as GPIO
import os
import time
import pycron
import threading

PIN_SENSOR = int(os.getenv('PIN_SENSOR', 13)) # GPIO 13, pin 27
PIN_POWERB = int(os.getenv('PIN_POWERB', 11)) # GPIO 11, pin 17
PIN_TOGGLE = int(os.getenv('PIN_TOGGLE', 15)) # GPIO 15, pin 22
PIN_BUZZER = int(os.getenv('PIN_BUZZER', 32)) # GPIO 32, pin 12

BUZZER_ENABLED = bool(os.getenv('BUZZER_ENABLED', True))
BUZZER_FREQUENCY = int(os.getenv('BUZZER_FREQUENCY', 300))
BUZZER_TIME = float(os.getenv('BUZZER_TIME', 0.1))

DEFAULT_STATE = bool(os.getenv('DEFAULT_STATE', False))
SCHEDULED_ON = os.getenv('SCHEDULED_ON', '0 8 * * *')
SCHEDULED_OFF = os.getenv('SCHEDULED_OFF', '0 9 * * *')
BUTTON_WAKE_MINUTES = float(os.getenv('BUTTON_WAKE_MINUTES', 5)) # in minutes


def throttle(wait_time):
    """
    Decorator that will throttle a function so that it is called only once every wait_time seconds
    If it is called multiple times, will run only the first time.
    See the test_throttle.py file for examples
    """

    def decorator(function):
        def throttled(*args, **kwargs):
            def call_function():
                return function(*args, **kwargs)

            if time.time() - throttled._last_time_called >= wait_time:
                call_function()
                throttled._last_time_called = time.time()

        throttled._last_time_called = 0
        return throttled

    return decorator

def getScreenState():
    currentState = (GPIO.input(PIN_SENSOR) == GPIO.HIGH)
    print(f"The screen is currently {'on' if currentState else 'off'}")
    return currentState

def setScreenState(newState):
    if newState != getScreenState():
        pushPowerButton()
        print(f"Turning screen {'on' if newState else 'off'}")

@throttle(5) # Ignore multiple calls within 5 seconds
def pushPowerButton():
    GPIO.output(PIN_POWERB, GPIO.LOW)
    time.sleep(0.2)
    GPIO.output(PIN_POWERB, GPIO.HIGH)

def beep():
    p = GPIO.PWM(PIN_BUZZER, BUZZER_FREQUENCY)
    p.start(50) # Start PWM at 50% duty cycle
    time.sleep(BUZZER_TIME)
    p.stop()

@throttle(1) # Ignore multiple calls within 1 second
def buttonPushed(channel):
    print("Button pushed!")
    if BUZZER_ENABLED:
        beep()

    setScreenState(True)

    # If the timer was already running, restart it
    if timerTurnOff.is_alive():
        print(" -> Restarting timer")
        timerTurnOff.cancel()
    print(f" -> Scheduling screen to turn off in {BUTTON_WAKE_MINUTES} minutes")
    timerTurnOff.start()



# Set GPIO mode: GPIO.BCM or GPIO.BOARD
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(PIN_SENSOR, GPIO.IN)
GPIO.setup(PIN_POWERB, GPIO.OUT)
GPIO.setup(PIN_TOGGLE, GPIO.IN)
GPIO.setup(PIN_BUZZER, GPIO.OUT)
GPIO.add_event_detect(PIN_TOGGLE, GPIO.RISING, callback=buttonPushed)  # add rising edge detection on a channel

timerTurnOff = threading.Timer(BUTTON_WAKE_MINUTES * 60, setScreenState, [False])

print(f"Screen is scheduled to turn on at '{SCHEDULED_ON}' and off at '{SCHEDULED_OFF}'.")

# Set screen state to default state
print(f"Waiting for {BUTTON_WAKE_MINUTES} minutes before turning screen {'on' if DEFAULT_STATE else 'off'}")
time.sleep(BUTTON_WAKE_MINUTES * 60)
setScreenState(DEFAULT_STATE)

while True:
    if pycron.is_now(SCHEDULED_ON):
        setScreenState(True)
    elif pycron.is_now(SCHEDULED_OFF):
        # If a timer is running, the screen will turn off on it's own
        if not timerTurnOff.is_alive():
            setScreenState(False)

    # Check again in a second
    time.sleep(1)
