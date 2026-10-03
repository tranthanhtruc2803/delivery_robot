import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

interface UARTConsoleProps {
  logs: string[];
}

export function UARTConsole({ logs }: UARTConsoleProps) {
  const consoleRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="flex-1 bg-[#d0bdf4] shadow-md rounded-lg p-4 flex flex-col min-h-0 border border-[#a28089]/20">
      <div className="flex items-center gap-2 mb-2">
        <Terminal className="w-5 h-5 text-[#8458B3]" />
        <h2 className="text-lg font-bold text-[#8458B3]">Communication Console</h2>
      </div>

      <div
        ref={consoleRef}
        className="flex-1 bg-white rounded border border-[#a28089]/40 p-3 font-mono text-xs overflow-y-auto min-h-0 shadow-inner"
      >
        {logs.length === 0 ? (
          <div className="text-[#a28089]/70 font-medium">Waiting for data...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="text-[#8458B3] mb-1 font-medium">
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
