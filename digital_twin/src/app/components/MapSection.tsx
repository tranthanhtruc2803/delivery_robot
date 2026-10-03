import { useState, useEffect, useRef, MouseEvent } from 'react';
import { Navigation, MapPin } from 'lucide-react';

interface MapSectionProps {
  position: { x: number; y: number; angle: number };
  lastUpdate: Date;
  autoNavigateMode: boolean;
  apiBaseUrl: string;
  onDestinationSet: (dest: {x: number, y: number}) => void;
}

export function MapSection({ position, lastUpdate, autoNavigateMode, apiBaseUrl, onDestinationSet }: MapSectionProps) {
  const [mapImage, setMapImage] = useState<string | null>(null);
  const [targetPos, setTargetPos] = useState<{x: number, y: number} | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  

  const isRealtime = Date.now() - lastUpdate.getTime() < 2000;

  // Fetch the LIDAR map periodically
  useEffect(() => {
    const fetchMap = async () => {
      try {
        // Add a timestamp to bypass browser caching!
        const response = await fetch(`${apiBaseUrl}/api/map?t=${Date.now()}`);
        const data = await response.json();
        if (data.status === 'success' && data.map_data) {
          // Expecting a base64 string from the backend
          setMapImage(data.map_data);
        }
      } catch (error) {
        console.error('Failed to fetch LIDAR map:', error);
      }
    };

    const interval = setInterval(fetchMap, 1000); // Poll every 1 second
    return () => clearInterval(interval);
  }, []);

  const handleMapClick = async (e: MouseEvent<HTMLDivElement>) => {
    if (!autoNavigateMode || !mapContainerRef.current) return;

    const rect = mapContainerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    // Clamp values
    const clampedX = Math.max(0, Math.min(100, x));
    const clampedY = Math.max(0, Math.min(100, y));

    const dest = { x: clampedX, y: clampedY };
    setTargetPos(dest);
    onDestinationSet(dest);

    try {
      await fetch(`${apiBaseUrl}/api/navigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dest)
      });
    } catch (error) {
      console.error('Failed to send navigation target:', error);
    }
  };

  return (
    <div className="flex-1 bg-[#d0bdf4] shadow-md rounded-lg p-4 flex flex-col min-h-0 border border-[#a28089]/20">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-bold text-[#8458B3]">Map View</h2>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isRealtime ? 'bg-emerald-500 shadow-sm' : 'bg-rose-500 shadow-sm'} animate-pulse`} />
            <span className="text-xs font-bold text-[#8458B3]">
              {isRealtime ? 'Real-time' : 'Delayed'}
            </span>
          </div>
          <div className="text-xs font-medium text-[#a28089]">
            {lastUpdate.toLocaleTimeString()}
          </div>
        </div>
      </div>

      <div 
        ref={mapContainerRef}
        onClick={handleMapClick}
        className={`flex-1 bg-[#e5eaf5] rounded border border-[#a28089]/40 relative overflow-hidden min-h-0 shadow-inner ${autoNavigateMode ? 'cursor-crosshair' : 'cursor-default'}`}
      >
        {/* Grid background */}
        <div className="absolute inset-0 opacity-20">
          <svg width="100%" height="100%" className="size-full">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#a28089" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>

        {/* NEW: LIDAR Map Image Layer */}
        {mapImage && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <img 
              src={mapImage} 
              alt="Real-time LIDAR Map" 
              className="w-full h-full object-contain opacity-90 mix-blend-multiply"
            />
          </div>
        )}

        {/* Car marker */}
        <div
          className="absolute transition-all duration-300"
          style={{
            left: `${position.x}%`,
            top: `${position.y}%`,
            transform: `translate(-50%, -50%) rotate(${position.angle}deg)`
          }}
        >
          <div className="relative">
            <Navigation className="w-8 h-8 text-[#8458B3] fill-[#8458B3] drop-shadow-md" />
            <div className="absolute inset-0 w-8 h-8 bg-[#8458B3]/20 rounded-full blur-xl animate-pulse" />
          </div>
        </div>

        {/* Target Destination marker */}
        {targetPos && (
          <div
            className="absolute transition-all duration-300"
            style={{
              left: `${targetPos.x}%`,
              top: `${targetPos.y}%`,
              transform: `translate(-50%, -100%)`
            }}
          >
            <div className="relative animate-bounce">
              <MapPin className="w-8 h-8 text-[#a28089] fill-[#a28089]/20 drop-shadow-sm" />
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-1 bg-[#a28089]/30 rounded-full blur-[2px]" />
            </div>
          </div>
        )}

        {/* Position info overlay */}
        <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur-sm px-3 py-2 rounded border border-[#a28089]/30 text-xs font-mono shadow-sm">
          <div className="text-[#8458B3] font-bold">X: {position.x.toFixed(1)}%</div>
          <div className="text-[#8458B3] font-bold">Y: {position.y.toFixed(1)}%</div>
          <div className="text-[#8458B3] font-bold">Angle: {position.angle.toFixed(0)}°</div>
        </div>
      </div>
    </div>
  );
}
