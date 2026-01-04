import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import './App.css';
import { IngestionForm } from './components/IngestionForm';
import { LogViewer } from './components/LogViewer';
import { ResultView } from './components/ResultView';
import { Settings, loadSettings } from './components/Settings';
import type { IngestionConfig, LogEntry, IngestionResult, AppSettings } from './types';

type AppState = 'idle' | 'running' | 'complete' | 'error';

function App() {
  const [state, setState] = useState<AppState>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [result, setResult] = useState<IngestionResult | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(loadSettings);

  useEffect(() => {
    const unlistenLog = listen<{ message: string; level: string }>('ingestion-log', (event) => {
      setLogs((prev) => [...prev, {
        timestamp: new Date().toISOString(),
        message: event.payload.message,
        level: event.payload.level as LogEntry['level'],
      }]);
    });

    return () => {
      unlistenLog.then((fn) => fn());
    };
  }, []);

  const handleSubmit = async (config: IngestionConfig) => {
    if (!settings.ingestionPath) {
      const errorResult: IngestionResult = {
        success: false,
        error: 'Please configure the Ingestion Script Path in Settings first',
        manifest: null,
        assetCount: 0,
        totalSize: 0,
      };
      setResult(errorResult);
      setState('error');
      return;
    }

    setState('running');
    setLogs([]);
    setResult(null);

    const sourceLabel = config.source === 'filesystem' 
      ? (config as { path: string }).path 
      : config.source.toUpperCase();
    
    const packLabel = config.source === 'filesystem' 
      ? (config as { packName: string }).packName 
      : 'all assets';
    
    const startEntry: LogEntry = {
      timestamp: new Date().toISOString(),
      message: `Starting ${config.source} ingestion: ${packLabel} from ${sourceLabel}`,
      level: 'info',
    };
    setLogs([startEntry]);

    try {
      let rustConfig;
      
      if (config.source === 'filesystem') {
        rustConfig = {
          path: config.path,
          name: config.packName,
          source: 'filesystem',
          tags: config.tags || [],
          license: config.licenseUrl || null,
          download_strategy: null,
          output_dir: settings.outputDirectory || null,
        };
      } else {
        rustConfig = {
          path: null,
          name: null,
          source: config.source,
          tags: [],
          license: null,
          download_strategy: config.downloadStrategy || 'metadata_only',
          output_dir: config.outputDirectory || settings.outputDirectory || null,
        };
      }

      const ingestionResult = await invoke<IngestionResult>('run_ingestion', {
        config: rustConfig,
        ingestionPath: settings.ingestionPath,
      });

      setResult(ingestionResult);
      setState(ingestionResult.success ? 'complete' : 'error');
    } catch (err) {
      const errorResult: IngestionResult = {
        success: false,
        error: err instanceof Error ? err.message : String(err),
        manifest: null,
        assetCount: 0,
        totalSize: 0,
      };
      setResult(errorResult);
      setState('error');
    }
  };

  const handleReset = () => {
    setState('idle');
    setLogs([]);
    setResult(null);
  };

  const handleSettingsClose = () => {
    setShowSettings(false);
    setSettings(loadSettings());
  };

  return (
    <main className="container">
      <header style={styles.header}>
        <h1 style={styles.title}>Game Asset Tracker</h1>
        <button
          onClick={() => setShowSettings(true)}
          style={styles.settingsButton}
          aria-label="Settings"
        >
          ⚙
        </button>
      </header>

      {showSettings ? (
        <Settings onClose={handleSettingsClose} />
      ) : state === 'idle' ? (
        <IngestionForm onSubmit={handleSubmit} disabled={false} />
      ) : state === 'running' ? (
        <div style={styles.runningContainer}>
          <div style={styles.spinner} />
          <p style={styles.runningText}>Ingesting assets...</p>
          <LogViewer logs={logs} />
        </div>
      ) : (
        <div style={styles.resultContainer}>
          <ResultView result={result} onReset={handleReset} />
          <LogViewer logs={logs} />
        </div>
      )}
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 'var(--space-lg)',
    paddingBottom: 'var(--space-md)',
    borderBottom: '1px solid var(--border-color)',
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  settingsButton: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    padding: 'var(--space-xs)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-secondary)',
    opacity: 0.8,
    transition: 'all 0.2s',
  },
  runningContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 'var(--space-lg)',
    width: '100%',
  },
  spinner: {
    width: 40,
    height: 40,
    border: '3px solid var(--border-color)',
    borderTopColor: 'var(--accent-color)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  runningText: {
    fontSize: '15px',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  resultContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-lg)',
    width: '100%',
  },
};

export default App;
