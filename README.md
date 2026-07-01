Disclaimer. This is a work in progress. Open source proof of concept provided. Screenshots and video provided. Documentation is subject to change.

NOTICE! Due to memory limits a second python file was created. sprites.py is required. Place next to code.py in the CIRCUITPY drive. The follwing lines need to be added to boot.py: "import displayio" and below that "displayio.release_displays()"

Clock + Metronome + Tuner wristwatch is the goal of this project. In addition. There are standalone files for each mode.

Dev Enviornment: Mu https://codewith.mu/en/, KiCAD https://www.kicad.org/

Circuitpython for QTpy RP2040: https://circuitpython.org/board/adafruit_qtpy_rp2040/

Circuitpython 10.x libraries: https://circuitpython.org/libraries

NOTE: Place the following in the lib folder: adafruit_bus_device folder, adafruit_display_text folder, adafruit_gc9a01a.mpy and adafruit_ticks.mpy. 

NOTE: Add the following to the requirements folder: adafruit_bus_device folder, adafruit_display_text folder and adafruit_gc9a01a folder.

Microcontroller: QTpy RP2040 https://www.adafruit.com/product/4900

Prototype 1, 2 and 3 Display: 1.28" Round TFT https://www.adafruit.com/product/6178 

Prototype 1 hardware: EYESPI BFF https://www.adafruit.com/product/5772, IoT Button BFF https://www.adafruit.com/product/5666, Vibration Mini Motor https://www.adafruit.com/product/1201, Piezo Buzzer https://www.adafruit.com/product/1740, LIPO Charger BFF https://www.adafruit.com/product/5397, 400mAh LIPO Battery https://www.adafruit.com/product/3898

Prototype 2 hardware: IoT Button BFF removed. Prototype board added. SMD parts replace THT parts. All SMD parts purchsed from https://www.digikey.com/ Buttons added. Piezo replaced with magnetic transducer. Schematic and board file provided. 

Prototype 3 hardware: EYESPI BFF removed. Prototype board updated. SMD FPC added. SMD vibration motor replaces THT vibration motor. 420mAh LIPO battery https://www.adafruit.com/product/4236 replaces 400mAh LIPO battery. 

Prototype 4 hardware: Prototype board updated. New 1.28 Display https://www.buydisplay.com/1-28-inch-tft-lcd-display-240x240-round-circle-screen-for-smart-watch, SMD FPC updated. QTpy dock added. Futher refinement is underway as I put protoboardV4 through testing.

Prototype 5 hardware: Circuit for display reset added. Circuit for backlight added. QTpy dock adjusted from 17.5mm to 18mm.

![ScreenShot](watch.jpg)

![ScreenShot](metronome.jpg)

![ScreenShot](tuner.jpg)

https://github.com/user-attachments/assets/00a04122-98c7-4e2a-a195-a43d13c6c467

Vibration circuit layout. A transistor and resistor are used to make it possible for the QTpy to control the motor with 3 volts. A diode is used as a flyback for when the motor stops running. The transistor connects to the black wire, the resistor and the diode. The black wire goes from the emitter lead of the transistor to ground. The resistor(100ohm) connects the base lead of the transistor to A1. The anode portion of the diode connects to the collector lead of the transistor. The cathode porton of the diode connects to the red wire. The red wire connects to 3.3 volts. The driver motor connects to each side of the diode. Blue to anode and red to cathode. 

Component list: 100Ω resistor, diode(1N4007) and transistor(2N2222)

![ScreenShot](vibcircuit.jpg)

Soldered vibration circuit.

![ScreenShot](vibcirsold.jpg)

https://github.com/user-attachments/assets/0c229e03-611d-4f90-9194-24d2ad153cdb

Soldered piezo.

https://github.com/user-attachments/assets/ea14efcf-dfc6-47f1-8c45-b138b7211cc2

LIPO BFF added. Backlight hack added(red wire at the top) to allow for screen dimming as a battery saving feature.

![ScreenShot](powered.jpg)

Screen dimming test. At the 10 second mark the screen dims.

https://github.com/user-attachments/assets/76fc044c-b8f3-486a-8c0e-50453308a22c

Prototype 2 board screenshots. Pre and post solder.

![ScreenShot](protoboardV2.jpg)

![ScreenShot](pbV2solder.jpg)

![ScreenShot](pbv2test.jpg)

Prototype 3 board screenshots. Pre and post solder.

![ScreenShot](protoboardV3.jpg)

![ScreenShot](pbV3solder.jpg)

Prototype 4a board screenshots. Pre and post solder.

![ScreenShot](protoboardV4.jpg)

![ScreenShot](pvV4AsolderF.jpg)

![ScreenShot](pvV4AsolderB.jpg)

Prototype 5a board screenshots. Pre and post solder.

