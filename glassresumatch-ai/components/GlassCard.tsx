import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverEffect?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', onClick, hoverEffect = false }) => {
  return (
    <div 
      onClick={onClick}
      className={`
        relative overflow-hidden
        bg-white/70
        backdrop-blur-xl 
        border border-white/60
        rounded-2xl 
        shadow-[0_4px_20px_-2px_rgba(0,0,0,0.05)]
        transition-all duration-300
        ${hoverEffect ? 'hover:bg-white/90 hover:border-white hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.1)] hover:-translate-y-1 cursor-pointer' : ''}
        ${className}
      `}
    >
      {/* Glossy reflection effect - subtle for light mode */}
      <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-white/40 to-transparent pointer-events-none" />
      
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};