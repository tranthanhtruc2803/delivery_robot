import { useState, useEffect, useRef } from 'react';
import { MapSection } from './components/MapSection';
import { DeliveryInfo } from './components/DeliveryInfo';
import { ControlPanel } from './components/ControlPanel';
import { UARTConsole } from './components/UARTConsole';

export default function App() {
  const [carPosition, setCarPosition] = useState({ x: 50, y: 50, angle: 0, speed: 0 });
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [uartLogs, setUartLogs] = useState<string[]>([]);
  const [targetDestination, setTargetDestination] = useState<{x: number, y: number} | null>(null);
  const [autoNavigateMode, setAutoNavigateMode] = useState(false);
  const [espConnected, setEspConnected] = useState(false);

  // API configuration - update with your Flask backend URL
  const API_BASE_URL = 'http://192.168.1.11:5000';


  // Fetch car position updates
  useEffect(() => {
    const fetchPosition = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/position`);
        const data = await response.json();
        setCarPosition(data.position);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('Failed to fetch position:', error);
      }
    };

    // Poll every 500ms for updates
    const interval = setInterval(fetchPosition, 500);
    return () => clearInterval(interval);
  }, []);

  // Fetch system status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/status`);
        const data = await response.json();
        setEspConnected(data.esp32_connected);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    };
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch UART logs
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/uart`);
        const data = await response.json();
        if (data.logs && data.logs.length > 0) {
          setUartLogs(prev => [...prev, ...data.logs].slice(-100));
        }
      } catch (error) {
        console.error('Failed to fetch UART logs:', error);
      }
    };

    const interval = setInterval(fetchLogs, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleControl = async (direction: 'up' | 'down' | 'left' | 'right' | 'stop') => {
    try {
      await fetch(`${API_BASE_URL}/api/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction })
      });
      setUartLogs(prev => [...prev, `> Command sent: ${direction.toUpperCase()}`]);
    } catch (error) {
      console.error('Failed to send control command:', error);
    }
  };

  const handleReconnect = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/reconnect`, { method: 'POST' });
      setUartLogs(prev => [...prev, `> Force reconnecting ESP32...`]);
    } catch (error) {
      console.error('Failed to reconnect:', error);
    }
  };

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#e5eaf5] text-[#8458B3] p-2 sm:p-4 flex flex-col gap-3 font-sans">
      <header className="flex items-center justify-between shrink-0 px-2">
        <h1 className="text-2xl font-bold text-[#8458B3] tracking-wide">
          Delivery Robot Admin
        </h1>
      </header>

      <div className="flex-1 grid grid-cols-3 gap-3 min-h-0">
        {/* Left column: Map */}
        <div className="col-span-2 flex flex-col min-h-0">
          <MapSection 
            position={carPosition} 
            lastUpdate={lastUpdate} 
            autoNavigateMode={autoNavigateMode}
            apiBaseUrl={API_BASE_URL}
            onDestinationSet={setTargetDestination}
          />
        </div>

        {/* Right column: Delivery Info, Controls and UART Console */}
        <div className="flex flex-col gap-3 min-h-0 overflow-y-auto pr-1 pb-1">
          <DeliveryInfo targetDestination={targetDestination} apiBaseUrl={API_BASE_URL} />
          <ControlPanel 
            onControl={handleControl} 
            isAutoMode={autoNavigateMode} 
            onToggleMode={() => setAutoNavigateMode(!autoNavigateMode)} 
            espConnected={espConnected}
            onReconnect={handleReconnect}
            speed={carPosition.speed || 0}
          />
          <UARTConsole logs={uartLogs} />
        </div>
      </div>
    </div>
  );
}
