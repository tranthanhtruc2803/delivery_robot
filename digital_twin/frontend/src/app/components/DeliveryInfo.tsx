import { useState } from 'react';
import { Lock, Unlock, MapPin } from 'lucide-react';

interface DeliveryInfoProps {
  targetDestination: { x: number; y: number } | null;
  apiBaseUrl: string;
}

export function DeliveryInfo({ targetDestination, apiBaseUrl }: DeliveryInfoProps) {
  const [pin, setPin] = useState('');
  const [status, setStatus] = useState<'locked' | 'unlocked' | 'error'>('locked');
  const [message, setMessage] = useState('');

  const handleUnlock = async () => {
    if (pin.length !== 4) {
      setStatus('error');
      setMessage('PIN must be 4 digits');
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/box`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
      });
      const data = await response.json();
      
      if (response.ok && data.status === 'success') {
        setStatus('unlocked');
        setMessage('Box unlocked successfully!');
        setPin('');
      } else {
        setStatus('error');
        setMessage(data.message || 'Invalid PIN');
      }
    } catch (error) {
      setStatus('error');
      setMessage('Network error');
    }
  };

  return (
    <div className="bg-[#d0bdf4] shadow-md rounded-lg p-4 border border-[#a28089]/20 flex flex-col gap-4">
      <h2 className="text-lg font-bold text-[#8458B3]">Delivery Info</h2>
      
      {/* Destination Status */}
      <div className="flex items-center gap-3 p-3 bg-[#e5eaf5] rounded-lg border border-[#a28089]/20 shadow-sm">
        <MapPin className="w-5 h-5 text-[#8458B3]" />
        <div className="flex-1">
          <div className="text-xs font-semibold text-[#a28089]">Current Destination</div>
          {targetDestination ? (
            <div className="font-mono text-[#8458B3] font-bold">
              X: {targetDestination.x.toFixed(1)}%, Y: {targetDestination.y.toFixed(1)}%
            </div>
          ) : (
            <div className="text-sm font-medium text-[#a28089] italic">No destination set</div>
          )}
        </div>
      </div>

      {/* Secure Box Unlock */}
      <div className="flex flex-col gap-2 p-3 bg-[#e5eaf5] rounded-lg border border-[#a28089]/20 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          {status === 'unlocked' ? (
            <Unlock className="w-4 h-4 text-emerald-500" />
          ) : (
            <Lock className="w-4 h-4 text-[#8458B3]" />
          )}
          <span className="text-sm font-bold text-[#8458B3]">Secure Delivery Box</span>
        </div>
        
        <div className="flex gap-2">
          <input
            type="password"
            maxLength={4}
            value={pin}
            onChange={(e) => {
              setPin(e.target.value.replace(/[^0-9]/g, ''));
              setStatus('locked');
              setMessage('');
            }}
            placeholder="Enter PIN"
            className="flex-1 bg-white border border-[#a28089]/40 rounded px-3 py-1.5 text-[#8458B3] placeholder-[#a28089]/50 focus:outline-none focus:border-[#8458B3] focus:ring-1 focus:ring-[#8458B3] font-mono tracking-widest text-center shadow-inner transition-all"
          />
          <button
            onClick={handleUnlock}
            disabled={pin.length !== 4 || status === 'unlocked'}
            className="bg-[#8458B3] text-white hover:bg-[#8458B3]/90 active:bg-[#8458B3] disabled:opacity-50 disabled:cursor-not-allowed px-4 py-1.5 rounded text-sm font-bold transition-all shadow hover:shadow-md active:scale-95"
          >
            Unlock
          </button>
        </div>
        
        {message && (
          <div className={`text-xs mt-1 font-bold ${status === 'unlocked' ? 'text-emerald-500' : 'text-rose-500'}`}>
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
