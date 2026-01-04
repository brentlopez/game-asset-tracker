import { useState, useEffect } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { AppSettings, DEFAULT_SETTINGS } from '../types';

interface Props {
  onClose: () => void;
}

const STORAGE_KEY = 'asset-tracker-settings';

const styles = {
  overlay: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    animation: 'fadeIn 0.2s ease-out',
  },
  modal: {
    backgroundColor: 'var(--bg-card)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--shadow-lg)',
    width: '480px',
    maxWidth: '90vw',
    border: '1px solid var(--border-color)',
    animation: 'slideUp 0.2s ease-out',
  },
  header: {
    padding: 'var(--space-md) var(--space-lg)',
    borderBottom: '1px solid var(--border-color)',
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  body: {
    padding: 'var(--space-lg)',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 'var(--space-md)',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 'var(--space-xs)',
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  pathRow: {
    display: 'flex',
    gap: 'var(--space-sm)',
  },
  pathInput: {
    flex: 1,
    padding: '8px 12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-color)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-secondary)',
    minHeight: '36px',
    cursor: 'default',
  },
  browseButton: {
    padding: '0 16px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-color)',
    backgroundColor: 'var(--bg-card)',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
    minHeight: '36px',
    transition: 'background-color 0.2s',
  },
  footer: {
    padding: 'var(--space-md) var(--space-lg)',
    borderTop: '1px solid var(--border-color)',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 'var(--space-sm)',
    backgroundColor: 'var(--bg-secondary)',
    borderBottomLeftRadius: 'var(--radius-lg)',
    borderBottomRightRadius: 'var(--radius-lg)',
  },
  cancelButton: {
    padding: '8px 16px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-color)',
    backgroundColor: 'var(--bg-card)',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    transition: 'background-color 0.2s',
  },
  saveButton: {
    padding: '8px 16px',
    borderRadius: 'var(--radius-sm)',
    border: 'none',
    backgroundColor: 'var(--accent-color)',
    color: '#fff',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    transition: 'background-color 0.2s',
  },
};

export function loadSettings(): AppSettings {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return DEFAULT_SETTINGS;
  
  const parsed = JSON.parse(stored) as Partial<AppSettings> | null;
  return parsed ? { ...DEFAULT_SETTINGS, ...parsed } : DEFAULT_SETTINGS;
}

export function saveSettings(settings: AppSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function Settings({ onClose }: Props) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const handleBrowseIngestion = async () => {
    const selected = await open({ directory: true, multiple: false });
    if (selected && typeof selected === 'string') {
      setSettings((s) => ({ ...s, ingestionPath: selected }));
    } else if (Array.isArray(selected) && selected.length > 0) {
      setSettings((s) => ({ ...s, ingestionPath: selected[0] }));
    }
  };

  const handleBrowseOutput = async () => {
    const selected = await open({ directory: true, multiple: false });
    if (selected && typeof selected === 'string') {
      setSettings((s) => ({ ...s, outputDirectory: selected }));
    } else if (Array.isArray(selected) && selected.length > 0) {
      setSettings((s) => ({ ...s, outputDirectory: selected[0] }));
    }
  };

  const handleSave = () => {
    saveSettings(settings);
    onClose();
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>Settings</div>
        <div style={styles.body}>
          <div style={styles.fieldGroup}>
            <label style={styles.label}>Ingestion Script Path</label>
            <div style={styles.pathRow}>
              <input
                style={styles.pathInput}
                type="text"
                value={settings.ingestionPath}
                onChange={(e) =>
                  setSettings((s) => ({ ...s, ingestionPath: e.target.value }))
                }
                placeholder="Path to ingestion directory..."
                readOnly
              />
              <button style={styles.browseButton} onClick={handleBrowseIngestion}>
                Browse
              </button>
            </div>
          </div>

          <div style={styles.fieldGroup}>
            <label style={styles.label}>Output Directory</label>
            <div style={styles.pathRow}>
              <input
                style={styles.pathInput}
                type="text"
                value={settings.outputDirectory}
                onChange={(e) =>
                  setSettings((s) => ({ ...s, outputDirectory: e.target.value }))
                }
                placeholder="Where to save manifests..."
                readOnly
              />
              <button style={styles.browseButton} onClick={handleBrowseOutput}>
                Browse
              </button>
            </div>
          </div>
        </div>
        <div style={styles.footer}>
          <button style={styles.cancelButton} onClick={onClose}>
            Cancel
          </button>
          <button style={styles.saveButton} onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
