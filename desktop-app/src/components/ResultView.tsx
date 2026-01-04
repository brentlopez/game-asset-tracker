import { openPath } from '@tauri-apps/plugin-opener';
import { IngestionResult } from '../types';

interface Props {
  result: IngestionResult | null;
  onReset: () => void;
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: 'var(--space-xl)',
    backgroundColor: 'var(--bg-card)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-md)',
    border: '1px solid var(--border-color)',
    gap: 'var(--space-md)',
  },
  icon: {
    fontSize: '48px',
    marginBottom: 'var(--space-sm)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    backgroundColor: 'var(--bg-secondary)',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    margin: 0,
    color: 'var(--text-primary)',
  },
  stats: {
    display: 'flex',
    gap: 'var(--space-xl)',
    marginTop: 'var(--space-sm)',
    padding: 'var(--space-md)',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-sm)',
    width: '100%',
    justifyContent: 'space-around',
    boxSizing: 'border-box' as const,
  },
  stat: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '4px',
  },
  statValue: {
    fontSize: '24px',
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  statLabel: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    fontWeight: 500,
  },
  errorMessage: {
    color: 'var(--error-color)',
    fontSize: '14px',
    textAlign: 'center' as const,
    maxWidth: '400px',
    padding: 'var(--space-md)',
    backgroundColor: 'rgba(255, 59, 48, 0.1)',
    borderRadius: 'var(--radius-sm)',
    lineHeight: '1.4',
  },
  buttonRow: {
    display: 'flex',
    gap: 'var(--space-md)',
    marginTop: 'var(--space-md)',
  },
  primaryButton: {
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    backgroundColor: 'var(--accent-color)',
    color: '#fff',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    transition: 'background-color 0.2s',
  },
  secondaryButton: {
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-color)',
    backgroundColor: 'transparent',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    transition: 'background-color 0.2s',
  },
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function ResultView({ result, onReset }: Props) {
  if (!result) return null;

  const handleViewManifest = async () => {
    if (result.manifest) {
      await openPath(result.manifest);
    }
  };

  if (result.success) {
    return (
      <div style={styles.container}>
        <div style={{ ...styles.icon, color: 'var(--success-color)' }}>✓</div>
        <h2 style={styles.title}>Ingestion Complete</h2>
        <div style={styles.stats}>
          <div style={styles.stat}>
            <span style={styles.statValue}>{result.assetCount}</span>
            <span style={styles.statLabel}>Assets</span>
          </div>
          <div style={styles.stat}>
            <span style={styles.statValue}>{formatBytes(result.totalSize)}</span>
            <span style={styles.statLabel}>Total Size</span>
          </div>
        </div>
        <div style={styles.buttonRow}>
          {result.manifest && (
            <button style={styles.primaryButton} onClick={handleViewManifest}>
              View Manifest
            </button>
          )}
          <button style={styles.secondaryButton} onClick={onReset}>
            New Ingestion
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={{ ...styles.icon, color: 'var(--error-color)' }}>✗</div>
      <h2 style={styles.title}>Ingestion Failed</h2>
      <p style={styles.errorMessage}>{result.error}</p>
      <div style={styles.buttonRow}>
        <button style={styles.primaryButton} onClick={onReset}>
          Try Again
        </button>
      </div>
    </div>
  );
}
