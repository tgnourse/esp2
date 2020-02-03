import serial

#ser = serial.Serial('/dev/tty.usbserial-141320')  # open serial port on Mac
ser = serial.Serial('/dev/ttyUSB1')  # open serial port on RPi
print(ser.name)

print("reading 000400003705")
ser.write(b'/?000400003705!\r\n')
print(ser.read(255))

print("reading 000400003718")
ser.write(b'/?000400003718!\r\n')
print(ser.read(255))

ser.close()