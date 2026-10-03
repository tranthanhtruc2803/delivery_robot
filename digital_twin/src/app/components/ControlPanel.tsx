import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, MousePointer2, Gamepad2 } from 'lucide-react';

interface ControlPanelProps {
  onControl: (direction: 'up' | 'down' | 'left' | 'right' | 'stop') => void;
  isAutoMode: boolean;
  onToggleMode: () => void;
}

export function ControlPanel({ onControl, isAutoMode, onToggleMode }: ControlPanelProps) {
  const buttonClass = "bg-[#e5eaf5] hover:bg-[#a0d2eb]/50 active:bg-[#a0d2eb] border border-[#a28089]/30 p-2 rounded-lg flex items-center justify-center transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <div className="bg-[#d0bdf4] shadow-md rounded-lg p-4 border border-[#a28089]/20 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-[#8458B3]">Controls</h2>
        
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
            onClick={() => onControl('up')}
            className={buttonClass}
            disabled={isAutoMode}
            aria-label="Move up"
          >
            <ArrowUp className="w-6 h-6 text-[#8458B3]" />
          </button>
          <div />

          {/* Middle row */}
          <button
            onClick={() => onControl('left')}
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
            onClick={() => onControl('right')}
            className={buttonClass}
            disabled={isAutoMode}
            aria-label="Move right"
          >
            <ArrowRight className="w-6 h-6 text-[#8458B3]" />
          </button>

          {/* Bottom row */}
          <div />
          <button
            onClick={() => onControl('down')}
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
