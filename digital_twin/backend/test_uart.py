import serial
import time

# Change to /dev/ttyTHS2 if needed
PORT = '/dev/ttyTHS1'
BAUD = 115200

print(f"--- UART Test Script ---")
try:
    print(f"Opening {PORT} at {BAUD} baud...")
    ser = serial.Serial(PORT, BAUD, timeout=1)
    
    print("Sending 'F' (Forward)...")
    ser.write(b'F')
    ser.flush()
    
    time.sleep(0.5)
    
    # Read anything that came back
    if ser.in_waiting > 0:
        received = ser.read(ser.in_waiting)
        print(f"RECEIVED BACK: {received}")
    else:
        print("Nothing received back.")
    
    print("Commands sent successfully!")
    ser.close()

except PermissionError:
    print(f"Permission denied to access {PORT}. Are you in the dialout group?")
    print("Try running: sudo usermod -a -G dialout $USER")
except Exception as e:
    print(f"Error: {e}")
