"""Python Menu for the Raspberry Pi 0w with a 1.44in display."""
import socket
import os
import subprocess
import sys
import atexit
from time import sleep
import RPi.GPIO as GPIO
from PIL import Image,ImageDraw,ImageFont,ImageColor
import LCD_1in44
import LCD_Config

atexit.register(GPIO.cleanup)

# pin numbers
KEY_UP_PIN     = 6
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13
KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16

# setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()
GPIO.setup(KEY_UP_PIN,      GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_DOWN_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_LEFT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_RIGHT_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_PRESS_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY1_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY2_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY3_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)

# state class used for main control
class State:
    def __init__(self, lcd):
        self.current_menu = None
        self.needs_rerender = False
        self.lcd = lcd
        self.menu_history = []

    def run(self):
        while True:
            sleep(1/30)
            if self.needs_rerender:
                image = self.current_menu.get_image(self.lcd)
                self.lcd.LCD_ShowImage(image,0,0)

    def set_menu(self, menu):
        if self.current_menu is not None:
            self.current_menu.unfocus()
            self.menu_history.append(self.current_menu)
        self.current_menu = menu
        self.current_menu.focus()
        self.needs_rerender = True

    def prev_menu(self):
        if len(self.menu_history) != 0:
            self.current_menu.unfocus()
            self.current_menu = self.menu_history.pop()
            self.current_menu.focus()
            self.needs_rerender = True

    def key_pressed(self, key):
        print(len(self.menu_history))
        
        if key == KEY_UP_PIN:
            self.current_menu.move_up()

        if key == KEY_DOWN_PIN:
            self.current_menu.move_down()

        if key == KEY1_PIN:
            self.current_menu.select_item()
        
        if key == KEY2_PIN:
            self.prev_menu()

        self.needs_rerender = True

    def key_released(self, key):
        pass


class Menu:
    def __init__(self, loop=True, text_color="WHITE", highlight_color="RED", background_color="BLACK"):
        self.menu_items = []
        self.menu_index = 0
        self.loop = loop
        self.background_color = background_color
        self.text_color = text_color
        self.highlight_color = highlight_color
        self.needs_redraw = True
        self.image = None

    def get_image(self, lcd):
        if self.needs_redraw:
            self.image = Image.new("RGB", (lcd.width, lcd.height), "BLACK")
            draw = ImageDraw.Draw(self.image)
            if len(self.menu_items) < 12:
                for index,item in enumerate(self.menu_items):
                    pos = (5,5+(index*10))
                    color = self.highlight_color if index==self.menu_index else self.text_color
                    text = item["dynamic_callback"]() if item["dynamic"] else item["name"]
                    draw.text(pos, text, color)
            self.needs_redraw = False
        else:
            return self.image

    def add_menu_item(self, name, callback=lambda: False, dynamic=False, dynamic_callback=lambda: ""):
        self.menu_items.append({
            "name":name,
            "callback":callback,
            "dynamic":dynamic,
            "dynamic_callback":dynamic_callback,
        })
        self.needs_redraw = True
        return self

    def select_item(self):
        self.menu_items[self.menu_index]["callback"]()

    def move_up(self):
        self.menu_index -= 1
        if self.loop:
            if self.menu_index < 0:
                self.menu_index = len(self.menu_items)-1
        else:
            if self.menu_index < 0:
                self.menu_index = 0
        self.needs_redraw = True

    def move_down(self):
        self.menu_index += 1
        if self.loop:
            if self.menu_index > len(self.menu_items)-1:
                self.menu_index = 0
        else:
            if self.menu_index > len(self.menu_items)-1:
                self.menu_index = len(self.menu_items)-1
        self.needs_redraw = True
    
    def focus(self):
        self.menu_index = 0

    def unfocus(self):
        pass


def get_ip_address():
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    addr=s.getsockname()[0]
    s.close()
    return addr


def get_user_count():
    users = subprocess.check_output(["last"]).decode(sys.stdout.encoding)
    return users.count("still logged in")


def reboot():
    GPIO.cleanup()
    os.system("sudo reboot")


def update():
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U',
               'git+https://github.com/Wdude04/Pi-Control-Menu.git#pi-control-menu'])
    os.execv(sys.executable, sys.argv)
    sys.exit()


def main():
    LCD = LCD_1in44.LCD()
    scan_dir = LCD_1in44.SCAN_DIR_DFT
    LCD.LCD_Init(scan_dir)
    LCD.LCD_Clear()
    state = State(LCD)

    GPIO.add_event_detect(KEY_UP_PIN, GPIO.FALLING, callback=state.key_pressed)
    GPIO.add_event_detect(KEY_DOWN_PIN, GPIO.FALLING, callback=state.key_pressed)
    GPIO.add_event_detect(KEY1_PIN, GPIO.FALLING, callback=state.key_pressed)
    GPIO.add_event_detect(KEY2_PIN, GPIO.FALLING, callback=state.key_pressed)

    network_menu = Menu(highlight_color="WHITE")
    network_menu.add_menu_item("name", dynamic=True, dynamic_callback=lambda: f"hostname: {socket.gethostname()}")
    network_menu.add_menu_item("ip", dynamic=True, dynamic_callback=lambda: f"ip: {get_ip_address()}")
    network_menu.add_menu_item("users", dynamic=True, dynamic_callback=lambda: f"users: {get_user_count()}")

    main_menu = Menu()
    main_menu.add_menu_item("network", callback=lambda: state.set_menu(network_menu))
    main_menu.add_menu_item("update", callback=update)
    main_menu.add_menu_item("exit", callback=sys.exit)
    main_menu.add_menu_item("reboot", callback=reboot)

    state.set_menu(main_menu)
    state.run()

	
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"> Exception: {e}")
        print("> Cleaning up GPIO")
        GPIO.cleanup()
        print("> Done")
        print("> Raising exception")
        raise e