import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, MousePointer2, Gamepad2, RefreshCw } from 'lucide-react';
import { useRef } from 'react';

interface ControlPanelProps {
  onControl: (direction: 'up' | 'down' | 'left' | 'right' | 'stop') => void;
  isAutoMode: boolean;
  onToggleMode: () => void;
  espConnected: boolean;
  onReconnect: () => void;
  speed: number;
}

export function ControlPanel({ onControl, isAutoMode, onToggleMode, espConnected, onReconnect, speed }: ControlPanelProps) {
  const buttonClass = "bg-[#e5eaf5] hover:bg-[#a0d2eb]/50 active:bg-[#a0d2eb] border border-[#a28089]/30 p-2 rounded-lg flex items-center justify-center transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const intervalRef = useRef<number | null>(null);

  const startCommand = (dir: 'up' | 'down' | 'left' | 'right') => {
    onControl(dir);
    if (intervalRef.current) window.clearInterval(intervalRef.current);
    intervalRef.current = window.setInterval(() => {
      onControl(dir);
    }, 200);
  };

  const stopCommand = () => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    onControl('stop');
  };

  return (
    <div className="bg-[#d0bdf4] shadow-md rounded-lg p-4 border border-[#a28089]/20 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-[#8458B3]">Controls</h2>
          <div className="flex items-center gap-2 bg-[#a0d2eb]/20 px-2 py-1 rounded-full ml-2 border border-[#8458B3]/20">
            <span className="text-xs font-mono font-bold text-[#8458B3]">
              {Math.abs(speed).toFixed(1)} cm/s
            </span>
          </div>
          <div className="flex items-center gap-2 ml-1">
            <div 
              className={`w-2.5 h-2.5 rounded-full shadow-sm ${espConnected ? 'bg-emerald-500' : 'bg-gray-400'} animate-pulse`} 
              title={espConnected ? "ESP32 Connected" : "ESP32 Disconnected"}
            />
            <button 
              onClick={onReconnect}
              className="p-1 rounded hover:bg-black/5 text-[#a28089] hover:text-[#8458B3] transition-colors"
              title="Force ESP32 Reconnect"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        
        {/* Mode Toggle */}
        <button
          onClick={onToggleMode}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all border shadow-sm ${
            isAutoMode 
              ? 'bg-[#a0d2eb] border-[#8458B3]/50 text-[#8458B3]'
              : 'bg-[#e5eaf5] border-[#a28089]/30 text-[#a28089] hover:text-[#8458B3]'
          }`}
        >
          {isAutoMode ? <MousePointer2 className="w-3.5 h-3.5" /> : <Gamepad2 className="w-3.5 h-3.5" />}
          {isAutoMode ? 'Auto Navigate' : 'Manual Control'}
        </button>
      </div>

      <div className="flex items-center justify-center">
        {/* Control buttons */}
        <div className="grid grid-cols-3 gap-2">
          {/* Top row */}
          <div />
          <button
            onPointerDown={() => startCommand('up')}
            onPointerUp={stopCommand}
            onPointerLeave={stopCommand}
            className={buttonClass}
            disabled={isAutoMode}
            aria-label="Move up"
          >
            <ArrowUp className="w-6 h-6 text-[#8458B3]" />
          </button>
          <div />

          {/* Middle row */}
          <button
            onPointerDown={() => startCommand('left')}
            onPointerUp={stopCommand}
            onPointerLeave={stopCommand}
            className={buttonClass}
            disabled={isAutoMode}
            aria-label="Move left"
          >
            <ArrowLeft className="w-6 h-6 text-[#8458B3]" />
          </button>
          <button
            onClick={() => onControl('stop')}
            className="w-12 h-12 rounded-full border-2 border-[#8458B3] bg-[#d0bdf4] hover:bg-[#8458B3]/20 active:bg-[#8458B3]/40 shadow-sm transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed mx-auto flex items-center justify-center"
            disabled={isAutoMode}
            aria-label="Emergency stop"
          >
            <div className="w-4 h-4 bg-[#8458B3] rounded-sm" />
          </button>
          <button
            onPointerDown={() => startCommand('right')}
            onPointerUp={stopCommand}
            onPointerLeave={stopCommand}
            className={buttonClass}
            disabled={isAutoMode}
            aria-label="Move right"
          >
            <ArrowRight className="w-6 h-6 text-[#8458B3]" />
          </button>

          {/* Bottom row */}
          <div />
          <button
            onPointerDown={() => startCommand('down')}
            onPointerUp={stopCommand}
            onPointerLeave={stopCommand}
            className={buttonClass}
            disabled={isAutoMode}
            aria-label="Move down"
          >
            <ArrowDown className="w-6 h-6 text-[#8458B3]" />
          </button>
          <div />
        </div>
      </div>
    </div>
  );
}
