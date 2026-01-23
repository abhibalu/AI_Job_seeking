/**
 * Frontend Logger Utility
 * Provides structured logging with timestamps and levels.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

class Logger {
    private isEnabled = true;

    private formatMessage(level: LogLevel, context: string, message: string, data?: any) {
        const timestamp = new Date().toISOString();
        const prefix = `[${timestamp}] [${level.toUpperCase()}] [${context}]`;
        return { prefix, message, data, timestamp };
    }

    private sendToServer(level: LogLevel, context: string, message: string, data?: any) {
        // Fire and forget log sending
        // Use simpler URL since we don't have access to env vars easily in this context
        const API_URL = 'http://localhost:8000/api/logs';

        try {
            fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level,
                    context,
                    message,
                    data: data ? JSON.stringify(data) : null,
                    timestamp: new Date().toISOString()
                }),
                keepalive: true // Ensure log is sent even if page unloads
            }).catch(err => {
                // Silent fail to avoid loops
            });
        } catch (e) {
            // Ignore errors
        }
    }

    debug(context: string, message: string, data?: any) {
        if (!this.isEnabled) return;
        const { prefix } = this.formatMessage('debug', context, message, data);
        console.debug(prefix, message, data || '');
        // Don't send debug to server to save bandwidth/noise
    }

    info(context: string, message: string, data?: any) {
        if (!this.isEnabled) return;
        const { prefix } = this.formatMessage('info', context, message, data);
        console.info(prefix, message, data || '');
        this.sendToServer('info', context, message, data);
    }

    warn(context: string, message: string, data?: any) {
        if (!this.isEnabled) return;
        const { prefix } = this.formatMessage('warn', context, message, data);
        console.warn(prefix, message, data || '');
        this.sendToServer('warn', context, message, data);
    }

    error(context: string, message: string, error?: any) {
        if (!this.isEnabled) return;
        const { prefix } = this.formatMessage('error', context, message, error);
        console.error(prefix, message, error || '');
        this.sendToServer('error', context, message, error);
    }
}

export const logger = new Logger();
