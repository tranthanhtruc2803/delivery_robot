# Digital Twin Car Monitor - Setup Guide

## Architecture

- **Frontend**: React + Tailwind CSS (runs in Figma Make or can be deployed)
- **Backend**: Flask Python server (runs on your device with car hardware)

## Backend Setup (Flask Server)

### 1. Install Python Dependencies

```bash
pip install flask flask-cors pyserial opencv-python
```

### 2. Configure Hardware Settings

Edit `flask_backend.py` and update these settings:

```python
SERIAL_PORT = '/dev/ttyUSB0'  # Linux/Mac, or 'COM3' for Windows
SERIAL_BAUD = 9600            # Match your UART baud rate
WEBCAM_INDEX = 0              # Camera index (0 for built-in, 1 for USB)
```

### 3. Run the Flask Server

```bash
python flask_backend.py
```

The server will start on `http://0.0.0.0:5000` and be accessible from other devices on your network.

### 4. Find Your Server IP Address

**Linux/Mac:**
```bash
ifconfig | grep "inet "
```

**Windows:**
```bash
ipconfig
```

Look for your local network IP (e.g., `192.168.1.100`)

## Frontend Setup (React App)

### 1. Update API Configuration

In `src/app/App.tsx`, update the API_BASE_URL:

```typescript
const API_BASE_URL = 'http://YOUR_FLASK_SERVER_IP:5000';
// Example: const API_BASE_URL = 'http://192.168.1.100:5000';
```

### 2. Access the Frontend

- If using Figma Make: Use the preview in Figma
- If deploying: Build and host the React app

## API Endpoints

The Flask backend provides these endpoints:

- `GET /api/position` - Get current car position
- `GET /api/uart` - Get UART console logs
- `POST /api/control` - Send control commands (up/down/left/right)
- `GET /api/webcam` - Webcam video stream
- `GET /health` - Health check

## UART Communication Protocol

### From Car to Backend

The backend expects position updates in this format:
```
POS:x,y,angle,speed
```

Example:
```
POS:45.5,60.2,90,25.3
```

- `x`: X position (0-100%)
- `y`: Y position (0-100%)
- `angle`: Heading angle in degrees (0-360)
- `speed`: Current speed (0-50, optional)

### From Backend to Car

Control commands sent:
- `FORWARD\n` - Up arrow pressed
- `BACKWARD\n` - Down arrow pressed
- `LEFT\n` - Left arrow pressed
- `RIGHT\n` - Right arrow pressed

## Troubleshooting

### Serial Port Issues

**Linux**: You may need permissions
```bash
sudo chmod 666 /dev/ttyUSB0
# Or add user to dialout group
sudo usermod -a -G dialout $USER
```

**Windows**: Check Device Manager for correct COM port

### Camera Not Working

- Verify camera index (try 0, 1, 2)
- Check camera permissions
- On Linux, ensure user is in `video` group

### CORS Errors

If you get cross-origin errors, ensure `flask-cors` is installed and CORS is enabled in the backend.

### Connection Refused

- Verify Flask server is running
- Check firewall settings allow port 5000
- Ensure frontend URL matches Flask server IP

## Running Both on Same Device

1. Start Flask backend: `python flask_backend.py`
2. Frontend will auto-connect to `http://localhost:5000`

## Running on Different Devices

1. Start Flask backend on device with car hardware
2. Note the IP address (e.g., 192.168.1.100)
3. Update frontend `API_BASE_URL` to `http://192.168.1.100:5000`
4. Access frontend from any device on the network
