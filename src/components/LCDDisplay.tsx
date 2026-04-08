import type { LCDContent } from '../types/parking';

interface LCDDisplayProps {
  content: LCDContent;
  title?: string;
  className?: string;
}

export default function LCDDisplay({ content, title, className = '' }: LCDDisplayProps) {
  const padLine = (text: string) => text.padEnd(20, ' ').slice(0, 20);

  return (
    <div className={`relative ${className}`}>
      {title && (
        <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label mb-2">
          {title}
        </div>
      )}
      <div className="lcd-container bg-[#0a1a0a] rounded-xl p-4 shadow-inner border border-[#1a3a1a] overflow-hidden relative">
        {/* Scan-line overlay */}
        <div className="absolute inset-0 pointer-events-none lcd-scanlines" />

        {/* LCD glow effect */}
        <div className="absolute inset-0 pointer-events-none rounded-xl"
          style={{
            boxShadow: 'inset 0 0 30px rgba(0, 255, 65, 0.06)',
          }}
        />

        {/* LCD Inner bezel */}
        <div className="bg-[#0d200d] rounded-lg p-3 border border-[#143014] relative">
          <div className="font-mono text-sm leading-relaxed tracking-wider space-y-0.5">
            {[content.line1, content.line2, content.line3, content.line4].map((line, i) => (
              <div
                key={i}
                className="lcd-line text-[#00ff41] relative overflow-hidden whitespace-pre"
                style={{
                  textShadow: '0 0 8px rgba(0, 255, 65, 0.6), 0 0 20px rgba(0, 255, 65, 0.3)',
                  fontFamily: '"Courier New", "Lucida Console", monospace',
                  fontSize: '13px',
                  letterSpacing: '2px',
                }}
              >
                {padLine(line)}
              </div>
            ))}
          </div>
        </div>

        {/* Corner screws decoration */}
        <div className="absolute top-2 left-2 w-1.5 h-1.5 rounded-full bg-[#2a2a2a] border border-[#3a3a3a]" />
        <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[#2a2a2a] border border-[#3a3a3a]" />
        <div className="absolute bottom-2 left-2 w-1.5 h-1.5 rounded-full bg-[#2a2a2a] border border-[#3a3a3a]" />
        <div className="absolute bottom-2 right-2 w-1.5 h-1.5 rounded-full bg-[#2a2a2a] border border-[#3a3a3a]" />
      </div>
    </div>
  );
}
