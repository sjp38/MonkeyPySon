#!/usr/bin/env monkeyrunner
# MonkeyPySon - GUI and some others.
# Author : SeongJae Park <sj38.park@gmail.com>

from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice

from java.awt import BorderLayout, Dimension, Robot, Color, Cursor, Toolkit, Point, Font
from java.awt.event import KeyListener, WindowFocusListener
from java.awt.image import BufferedImage
from java.io import ByteArrayInputStream
from java.lang import System
from javax.imageio import ImageIO
from javax.swing import JButton, JFrame, JLabel, JPanel, JTextArea, JScrollPane, ScrollPaneConstants, BoxLayout, JTextField
from javax.swing.event import MouseInputAdapter
from pawt import swing

import os
import sys
import threading
import time


if System.getProperty("os.name").startswith("Windows"):
    import os
    srcFileDir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(srcFileDir)
    sys.path = [srcFileDir] + sys.path


REMAP_WIDTH = 480
REMAP_HEIGHT = 800
MARGIN = 10

CONNECTION_TIMEOUT = 5000

nextPort = 6789

robot = Robot()
connectedDevices = []
devConnListener = None

class Device:
    serialno = None
    mdevice = None
    socket = None
    cursorRatio = None
    productName = None
    focused = None

    def __init__(self):
        pass

    def __init__(self, serial, mdev, sock, ratio, name):
        self.serialno = serial
        self.mdevice = mdev
        self.socket = sock
        self.cursorRatio = ratio
        self.productName = name

    def __str__(self):
        return "[Device] name : %s serialno : %s mdevice : %s socket : %s cursorRatio : %s" % (self.productName, self.serialno, self.mdevice, self.socket, self.cursorRatio)

    def __repr__(self):
        return self.__str__()

def startLookingDevices():
    DevicePNPerThread().run()


class DevicePNPerThread(threading.Thread):
    def run(self):
        self.stop = False

    def run(self):
        global connectedDevices
        global REMAP_WIDTH
        global REMAP_HEIGHT
        while(1):
            changed = False
            usbConnected = getUsbConnectedDevices()
            newConnectedDevices = []
            for serialno in usbConnected:
                reused = False
                # Recycle is good habit.
                for dev in connectedDevices:
                    if serialno == dev.serialno:
                        newConnectedDevices.append(dev)
                        connectedDevices.remove(dev)
                        reused = True
                        break
                if not reused:
                    changed = True
                    mdevice = MonkeyRunner.waitForConnection(CONNECTION_TIMEOUT, serialno)

                    width = mdevice.getProperty("display.width")
                    height = mdevice.getProperty("display.height")
                    resolScaleRatioX = float(width) / REMAP_WIDTH
                    resolScaleRatioY = float(height) / REMAP_HEIGHT
                    resolScaleRatio = (resolScaleRatioX, resolScaleRatioY)

                    name = mdevice.getProperty("build.model")

                    # TODO : Reuse reusable port number.
                    global nextPort
                    nextPort += 1
                    cmd = "adb -s %s forward tcp:%d tcp:9991" % (serialno, nextPort)
                    os.popen(cmd)
                    socket = connectTo(nextPort)
                    
                    device = Device(serialno, mdevice, socket, resolScaleRatio, name)
                    newConnectedDevices.append(device)
            # Close unnecessary sockets
            for device in connectedDevices:
                changed = True
                device.socket.close()

            connectedDevices = newConnectedDevices
            if changed:
                nofocus = True
                for device in connectedDevices:
                    if device.focused:
                        noficus = False
                        break
                if nofocus:
                    connectedDevices[0].focused = True
                notifyCurrentDevices()
                print "new connected devices are : ", newConnectedDevices

            time.sleep(1)

def getUsbConnectedDevices():
    f = os.popen("adb devices")
    results = f.readlines()
    f.close()
    parsed = []
    for result in results[1:-1]:
        parsed.append(result.split()[0])
    return parsed



import socket

def connectTo(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect(("127.0.0.1", port))
    return sock

# SHOW <x axis> <y axis> ["pressed"]
def showCursor(sock, x, y, isPressed):
    query = "SHOW %d %d" % (x,y)
    if isPressed:
        query += " pressed"
    length = "%03d" % len(query)
    sock.sendall(length)
    sock.sendall(query)

# HIDE
def hideCursor(sock):
    query = "HIDE"
    length = "%03d" % len(query)
    sock.sendall(length)
    sock.sendall(query)




contentPane = None

def startGui():
    frame = JFrame("MonkeyPySon")
    frame.setContentPane(getContentPane())
    frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE)
    frame.pack()
    frame.setVisible(True)
    frame.addWindowFocusListener(GuiWindowFocusListener())
    startLookingDevices()

mainScreen = None
mainScreenImg = None
def getContentPane():
    global contentPane
    global REMAP_WIDTH
    global REMAP_HEIGHT
    global MARGIN
    if not contentPane:
        global mainScreen
        global mainScreenImg
        mainScreen = JLabel()

        cursorImg = BufferedImage(16,16,BufferedImage.TYPE_INT_ARGB)
        blankCursor = Toolkit.getDefaultToolkit().createCustomCursor(cursorImg, Point(0,0), "blank cursor")
        mainScreen.setCursor(blankCursor)
        mainScreen.setPreferredSize(
                Dimension(REMAP_WIDTH + MARGIN, REMAP_HEIGHT + MARGIN))
        mainScreen.setText("main screen!")
        image = BufferedImage(REMAP_WIDTH + MARGIN, REMAP_HEIGHT + MARGIN
                , BufferedImage.TYPE_INT_ARGB)
        g = image.createGraphics()
        g.setColor(Color.BLACK)
        g.fillRect(0, 0, REMAP_WIDTH + MARGIN, REMAP_HEIGHT + MARGIN)
        g.setColor(Color.WHITE)
        g.setFont(Font("Serif", Font.BOLD, 20))
        g.drawString("Cursor will display on your device.", 50, 30)
        mainScreenImg = image
        mainScreen.setIcon(swing.ImageIcon(image))

        mouseListener = ScrMouseListener()
        mainScreen.addMouseListener(mouseListener)
        mainScreen.addMouseMotionListener(mouseListener)
        mainScreen.addMouseWheelListener(mouseListener)

        keyListener = ScrKeyListener()
        mainScreen.addKeyListener(keyListener)
        
        mainScreen.setFocusable(True)

        scrPanel = JPanel()
        scrPanel.setLayout(BoxLayout(scrPanel, BoxLayout.Y_AXIS))
        scrPanel.add(mainScreen)


        contentPane = JPanel()
        contentPane.setLayout(BorderLayout())
        contentPane.add(scrPanel, BorderLayout.WEST)
#        contentPAne.add(controlPanel(). BorderLayout.EAST)

    return contentPane

def notifyCurrentDevices():
    global mainScreenImg
    global mainScreen
    global connectedDevices

    g = mainScreenImg.createGraphics()
    g.setFont(Font("Monospaced", Font.BOLD, 13))
    g.drawString("[Detected devices]", 70, 100)


    g.setColor(Color.BLACK)
    g.fillRect(70, 100, REMAP_WIDTH + MARGIN, REMAP_HEIGHT + MARGIN)

    g.setFont(Font("Monospaced", Font.PLAIN, 13))
    g.setColor(Color.GRAY)
    g.setBackground(Color.BLACK)

    for device in connectedDevices:
        text = "%s(%s)" % (device.productName, device.serialno)
        if device.focused:
            g.setColor(Color.WHITE)
            text = "Focused : " + text
        g.drawString(text, 70, 100 + 30*(connectedDevices.index(device)+1))
        if device.focused:
            g.setColor(Color.GRAY)
    mainScreen.setIcon(swing.ImageIcon(mainScreenImg))

class GuiWindowFocusListener(WindowFocusListener):
    def windowGainedFocus(self, event):
        global mainScreen
        basePoint = mainScreen.getLocationOnScreen()

        robot.mouseMove(int(basePoint.getX() + REMAP_WIDTH / 2), int(basePoint.getY() + REMAP_HEIGHT / 2))

    def windowLostFocus(self, event):
        pass

def calcAxis(value, device, isXAxis):
    scaleRatio = 1
    if isXAxis:
        scaleRatio = device.cursorRatio[0]
    else:
        scaleRatio = device.cursorRatio[1]
    return int(value * scaleRatio)

class ScrMouseListener(MouseInputAdapter):
    def __init__(self):
        self.dragging = False
        self.time1 = None
        self.xy1 = None
        self.lastAxis = None

    def mousePressed(self, event):
        for device in connectedDevices:
            if not device.focused: continue
            x = calcAxis(event.getX() - (MARGIN / 2), device, True)
            y = calcAxis(event.getY() - (MARGIN / 2), device, False)
            showCursor(device.socket, x, y, True)
            device.mdevice.touch(x, y, MonkeyDevice.DOWN)
            self.time1 = time.time()
            self.xy1 = (x, y)
        

    def mouseReleased(self, event):
        for device in connectedDevices:
            if not device.focused: continue
            x = calcAxis(event.getX() - (MARGIN / 2), device, True)
            y = calcAxis(event.getY() - (MARGIN / 2), device, False)

            showCursor(device.socket, x, y, False)
            if self.dragging:
                self.dragging = False
                time2 = time.time()
                device.mdevice.drag(self.xy1, (x, y), time2 - self.time1)
                return
            device.mdevice.touch(x, y, MonkeyDevice.UP)

    def moveFocus(self, device, toLeft, y):
        index = connectedDevices.index(device)
        print "index : ", index
        newXAxis = MARGIN / 2
        if toLeft:
            newFocusIndex = index+1
            newXAxis += REMAP_WIDTH
        else:
            newFocusIndex = index-1
        print "newFocusIndex : ", newFocusIndex
        device.focused = False
        connectedDevices[newFocusIndex].focused = True
        hideCursor(device.socket)
        basePoint = mainScreen.getLocationOnScreen()
        robot.mouseMove(int(basePoint.getX() + newXAxis), int(basePoint.getY() + y))
        notifyCurrentDevices()

    def processMouseMove(self, event):
        global mainScreen
        global connectedDevices
        x = event.getX()
        y = event.getY()
        # Move focus to next
        margin = MARGIN / 2
        leftLimit = margin
        rightLimit = REMAP_WIDTH + margin
        result = False

        focusChanged = False
        basePoint = mainScreen.getLocationOnScreen()
        
        self.lastAxis = (int(basePoint.getX()) + x, int(basePoint.getY()) + y)

        if x < leftLimit:
            for device in connectedDevices:
                if not device.focused: continue
                if connectedDevices.index(device) < len(connectedDevices) - 1:
                    print "move focus left!!!"
                    self.moveFocus(device, True, y)
                    focusChanged = True

        elif x > rightLimit:
            for device in connectedDevices:
                if not device.focused: continue
                if connectedDevices.index(device) > 0:
                    print "move focus right!!!"
                    self.moveFocus(device, False, y)
                    focusChanged = True
                else:
                    self.lastAxis = None
        return focusChanged

    def mouseDragged(self, event):
        if self.processMouseMove(event):
            self.dragging = False
            return
        for device in connectedDevices:
            if not device.focused: continue
            x = calcAxis(event.getX() - (MARGIN / 2), device, True)
            y = calcAxis(event.getY() - (MARGIN / 2), device, False)
            showCursor(device.socket, x, y, True)
            self.dragging = True


    def mouseMoved(self, event):
        if self.processMouseMove(event): return
        for device in connectedDevices:
            if not device.focused: continue
            x = calcAxis(event.getX() - (MARGIN / 2), device, True)
            y = calcAxis(event.getY() - (MARGIN / 2), device, False)

            showCursor(device.socket, x, y, False)

    def mouseExited(self, event):
        if self.lastAxis: robot.mouseMove(self.lastAxis[0], self.lastAxis[1])

    def mouseWheelMoved(self, event):
        notches = event.getWheelRotation()
        direction = ""
        if notches < 0:
            direction = "UP"
        else:
            direction = "DOWN"
        for device in connectedDevices:
            if not device.focused: continue
            device.press("KEYCODE_" + direction, MonkeyDevice.DOWN_AND_UP)

FUNCTION_KEY_MAP = {"F1":"HOME",
        "F2":"BACK",
        "F3":"MENU",
        "F4":"SEARCH",
        "F5":"POWER",
        "F6":"VOLUME_UP",
        "F7":"VOLUME_DOWN",
        "F8":"CALL",
        "F9":"ENDCALL",
        "BACKSPACE":"DEL",
        "UP":"DPAD_UP",
        "DOWN":"DPAD_DOWN",
        "LEFT":"DPAD_LEFT",
        "RIGHT":"DPAD_RIGHT"
        }

metaKeyState = {"SHIFT":False, "ALT":False, "CTRL":False}
class ScrKeyListener(KeyListener):

    def processKey(self, event, isDown):
        global metaKeyState
        keyCode = event.getKeyText(event.getKeyCode()).upper()
        if System.getProperty("os.name").startswith("Mac"):
            if keyCode == u'\u2423': keyCode = "SPACE"
            else:
                keyCode = keyCode.encode("utf-8")
                if "\xe2\x87\xa7" == keyCode: keyCode= "SHIFT"
                elif "\xe2\x8c\xa5" == keyCode: keyCode= "ALT"
                elif "\xe2\x8c\x83" == keyCode: keyCode= "CTRL"
                elif event.getKeyCode() == 8: keyCode = "DEL"
        if FUNCTION_KEY_MAP.has_key(keyCode):
            keyCode = FUNCTION_KEY_MAP[keyCode]
        action = MonkeyDevice.DOWN_AND_UP
        if isDown:
            action = MonkeyDevice.DOWN
        else:
            action = MonkeyDevice.UP
        if keyCode in metaKeyState.keys():
            keyCode += "_LEFT"
        for device in connectedDevices:
            if not device.focused: continue
            device.mdevice.press("KEYCODE_" + keyCode, action)

    def keyPressed(self, event):
        self.processKey(event, True)

    def keyReleased(self, event):
        self.processKey(event, False)

    def keyTyped(self, event):
        pass


if __name__ == "__main__":
    startGui()
    while(1):
        userInput = raw_input(">>> ")
        if userInput == "exit":
            break
