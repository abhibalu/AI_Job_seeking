import React, { useState, useEffect, useRef } from 'react';

interface TypewriterWaitStateProps {
    /** Messages to display in sequence, one character at a time. */
    messages: string[];
    /** Called once all messages have finished typing. */
    onComplete: () => void;
    /**
     * sessionStorage key to track "already shown this session".
     * When set: if the key exists in sessionStorage, onComplete fires immediately
     * (skips animation). Written to sessionStorage when the last message finishes.
     */
    sessionKey?: string;
    /** Characters per second equivalent: ms per character. Default 30. */
    speed?: number;
    /** Pause between messages in ms. Default 800. */
    delayBetweenMessages?: number;
    /** Optional CSS class override for the container. */
    className?: string;
}

/**
 * Typewriter animation through an array of messages.
 * Uses sessionStorage to avoid replaying on page refresh (ADR-0009).
 */
export const TypewriterWaitState: React.FC<TypewriterWaitStateProps> = ({
    messages,
    onComplete,
    sessionKey,
    speed = 30,
    delayBetweenMessages = 800,
    className = '',
}) => {
    const [displayed, setDisplayed] = useState('');
    const [msgIdx, setMsgIdx] = useState(0);
    const [charIdx, setCharIdx] = useState(0);
    const [done, setDone] = useState(false);
    const onCompleteRef = useRef(onComplete);
    useEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);

    // Skip if already seen this session
    useEffect(() => {
        if (sessionKey && sessionStorage.getItem(`ootocv_tw_${sessionKey}`)) {
            onCompleteRef.current();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionKey]);

    useEffect(() => {
        if (done) return;

        const msg = messages[msgIdx] ?? '';

        if (charIdx < msg.length) {
            const t = setTimeout(() => {
                setDisplayed(msg.slice(0, charIdx + 1));
                setCharIdx(c => c + 1);
            }, speed);
            return () => clearTimeout(t);
        }

        // Message fully typed — pause then advance
        const t = setTimeout(() => {
            if (msgIdx + 1 < messages.length) {
                setMsgIdx(m => m + 1);
                setCharIdx(0);
                setDisplayed('');
            } else {
                setDone(true);
                if (sessionKey) {
                    sessionStorage.setItem(`ootocv_tw_${sessionKey}`, 'true');
                }
                onCompleteRef.current();
            }
        }, delayBetweenMessages);

        return () => clearTimeout(t);
    }, [done, msgIdx, charIdx, messages, speed, delayBetweenMessages, sessionKey]);

    if (done) return null;

    return (
        <div className={`flex items-center gap-2 font-mono text-sm text-gray-500 ${className}`}>
            <span>{displayed}</span>
            {/* Blinking cursor */}
            <span className="inline-block w-[6px] h-[13px] bg-gray-500 animate-pulse align-middle" />
        </div>
    );
};
