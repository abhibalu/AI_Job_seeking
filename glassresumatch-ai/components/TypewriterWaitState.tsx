/**
 * TypewriterWaitState.tsx — OotoCV reference verbatim.
 *
 * Three memory-leak fixes baked in (per the reference spec):
 *   - pauseTimer cleared on unmount
 *   - onComplete ref-stabilised
 *   - messages snapshotted at mount via ref
 * Use `key={...}` on the parent to swap message sets.
 */
import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';

import { cn } from '../lib/utils';

interface TypewriterWaitStateProps {
  key?: string | number;
  messages: string[];
  onComplete?: () => void;
  speed?: number;
  delayBetweenMessages?: number;
  compact?: boolean;
}

export const TypewriterWaitState: React.FC<TypewriterWaitStateProps> = ({
  messages,
  onComplete,
  speed = 30,
  delayBetweenMessages = 1500,
  compact = false,
}) => {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');

  // Ref-stabilise onComplete — prevents handler-recreation from restarting the effect.
  const onCompleteRef = useRef(onComplete);
  useEffect(() => { onCompleteRef.current = onComplete; });

  // Snapshot messages at mount so literal-array prop changes don't restart.
  // To swap message sets, change the `key` prop on this component.
  const messagesRef = useRef(messages);

  useEffect(() => {
    if (currentMessageIndex >= messagesRef.current.length) {
      onCompleteRef.current?.();
      return;
    }

    const fullText = messagesRef.current[currentMessageIndex];
    let currentIndex = 0;
    let pauseTimer: ReturnType<typeof setTimeout> | undefined;

    const typingInterval = setInterval(() => {
      if (currentIndex <= fullText.length) {
        setDisplayedText(fullText.slice(0, currentIndex));
        currentIndex++;
      } else {
        clearInterval(typingInterval);
        pauseTimer = setTimeout(() => {
          setCurrentMessageIndex((prev) => prev + 1);
        }, delayBetweenMessages);
      }
    }, speed);

    return () => {
      clearInterval(typingInterval);
      if (pauseTimer) clearTimeout(pauseTimer);
    };
  }, [currentMessageIndex, speed, delayBetweenMessages]);

  return (
    <div className={cn('font-mono text-sm text-gray-400 flex flex-col items-start justify-center h-full', !compact && 'min-h-[200px] max-w-lg mx-auto')}>
      <div className="space-y-2 w-full">
        {!compact && messagesRef.current.slice(0, currentMessageIndex).map((msg, idx) => (
          <div key={idx} className="opacity-50 flex">
            <span className="text-accent mr-2">→</span>
            <span>{msg}</span>
          </div>
        ))}
        {currentMessageIndex < messagesRef.current.length && (
          <div className="flex text-gray-200">
            <span className="text-accent mr-2">→</span>
            <span>
              {displayedText}
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 0.8, ease: 'linear' }}
                className="inline-block w-2 h-4 bg-accent ml-1 align-middle"
              />
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
