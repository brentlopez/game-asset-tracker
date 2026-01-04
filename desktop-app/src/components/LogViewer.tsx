import { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

interface Props {
  logs: LogEntry[];
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: '#1e1e1e',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-md)',
    overflow: 'hidden',
    width: '100%',
    border: '1px solid var(--border-color)',
  },
  header: {
    padding: '8px 16px',
    backgroundColor: '#252526',
    fontSize: '12px',
    fontWeight: 600,
    color: '#999',
    borderBottom: '1px solid #333',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  logArea: {
    height: '300px',
    overflowY: 'auto' as const,
    padding: '12px 16px',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    lineHeight: '1.6',
    color: '#d4d4d4',
  },
  entry: {
    display: 'flex',
    gap: '12px',
    marginBottom: '4px',
  },
  timestamp: {
    color: '#666',
    flexShrink: 0,
    userSelect: 'none' as const,
  },
  message: {
    wordBreak: 'break-word' as const,
    whiteSpace: 'pre-wrap' as const,
  },
  empty: {
    color: '#666',
    fontStyle: 'italic' as const,
    textAlign: 'center' as const,
    marginTop: '20px',
  },
};

const levelColors: Record<LogEntry['level'], string> = {
  info: '#d4d4d4',
  warn: '#cca700',
  error: '#f48771',
};

export function LogViewer({ logs }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>Output Log</div>
      <div style={styles.logArea} ref={scrollRef}>
        {logs.length === 0 ? (
          <div style={styles.empty}>Waiting for ingestion to start...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} style={styles.entry}>
              <span style={styles.timestamp}>{log.timestamp}</span>
              <span style={{ ...styles.message, color: levelColors[log.level] }}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
