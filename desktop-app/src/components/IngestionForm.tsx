import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { IngestionConfig, SourceType, FabDownloadStrategy, UasDownloadStrategy } from '../types';

interface Props {
  onSubmit: (config: IngestionConfig) => void;
  disabled: boolean;
}

const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 'var(--space-lg)',
    padding: 'var(--space-xl)',
    backgroundColor: 'var(--bg-card)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-md)',
    border: '1px solid var(--border-color)',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 'var(--space-sm)',
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: 'var(--space-xs)',
  },
  input: {
    padding: '8px 12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-color)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-input)',
    color: 'var(--text-primary)',
    minHeight: '36px',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  },
  select: {
    padding: '8px 12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-color)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-input)',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    minHeight: '36px',
    appearance: 'none' as const,
    backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    backgroundSize: '16px',
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
  submitButton: {
    padding: '12px 24px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    backgroundColor: 'var(--accent-color)',
    color: '#fff',
    cursor: 'pointer',
    fontSize: '15px',
    fontWeight: 600,
    marginTop: 'var(--space-md)',
    transition: 'background-color 0.2s, transform 0.1s',
  },
  submitButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
    backgroundColor: 'var(--text-secondary)',
  },
  infoBox: {
    padding: '12px 16px',
    borderRadius: 'var(--radius-sm)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: '1.4',
  },
  warningBox: {
    padding: '12px 16px',
    borderRadius: 'var(--radius-sm)',
    backgroundColor: 'rgba(255, 159, 10, 0.1)',
    border: '1px solid var(--warning-color)',
    fontSize: '13px',
    color: 'var(--warning-color)',
    lineHeight: '1.4',
  },
};

export function IngestionForm({ onSubmit, disabled }: Props) {
  const [source, setSource] = useState<SourceType>('filesystem');
  const [path, setPath] = useState('');
  const [packName, setPackName] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [licenseUrl, setLicenseUrl] = useState('');
  const [fabDownloadStrategy, setFabDownloadStrategy] = useState<FabDownloadStrategy>('metadata_only');
  const [uasDownloadStrategy, setUasDownloadStrategy] = useState<UasDownloadStrategy>('metadata_only');
  const [outputDir, setOutputDir] = useState('');

  const isFilesystem = source === 'filesystem';
  const isMarketplace = source === 'fab' || source === 'uas';

  const filesystemValid = path.trim() !== '' && packName.trim() !== '';
  const marketplaceValid = outputDir.trim() !== '';
  const isValid = isFilesystem ? filesystemValid : marketplaceValid;
  const canSubmit = isValid && !disabled;

  const handleBrowse = async () => {
    const selected = await open({ directory: true, multiple: false });
    if (selected && typeof selected === 'string') {
      setPath(selected);
    } else if (Array.isArray(selected) && selected.length > 0) {
      setPath(selected[0]);
    }
  };

  const handleOutputBrowse = async () => {
    const selected = await open({ directory: true, multiple: false });
    if (selected && typeof selected === 'string') {
      setOutputDir(selected);
    } else if (Array.isArray(selected) && selected.length > 0) {
      setOutputDir(selected[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    if (isFilesystem) {
      onSubmit({
        source,
        path,
        packName,
        tags,
        licenseUrl: licenseUrl.trim() || null,
      });
    } else if (source === 'fab') {
      onSubmit({
        source: 'fab',
        downloadStrategy: fabDownloadStrategy,
        outputDirectory: outputDir,
      });
    } else {
      onSubmit({
        source: 'uas',
        downloadStrategy: uasDownloadStrategy,
        outputDirectory: outputDir,
      });
    }
  };

  const handleSourceChange = (newSource: SourceType) => {
    setSource(newSource);
    setPath('');
    setPackName('');
    setTagsInput('');
    setLicenseUrl('');
  };

  return (
    <form style={styles.form} onSubmit={handleSubmit}>
      <div style={styles.fieldGroup}>
        <label style={styles.label}>Source Type</label>
        <select
          style={styles.select}
          value={source}
          onChange={(e) => handleSourceChange(e.target.value as SourceType)}
          disabled={disabled}
        >
          <option value="filesystem">Filesystem</option>
          <option value="fab">Fab (Epic Games)</option>
          <option value="uas">Unity Asset Store</option>
        </select>
      </div>

      {source === 'fab' && (
        <div style={styles.infoBox}>
          FAB uses credentials from Epic Games Launcher. Make sure you're logged into the Epic Games Launcher on this machine.
        </div>
      )}

      {source === 'uas' && (
        <div style={styles.infoBox}>
          UAS uses credentials from Unity Hub. Make sure you're logged into Unity Hub on this machine.
        </div>
      )}

      {isFilesystem && (
        <>
          <div style={styles.fieldGroup}>
            <label style={styles.label}>Asset Folder *</label>
            <div style={styles.pathRow}>
              <input
                style={styles.pathInput}
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="Select a folder..."
                readOnly
              />
              <button
                type="button"
                style={styles.browseButton}
                onClick={handleBrowse}
                disabled={disabled}
              >
                Browse
              </button>
            </div>
          </div>

          <div style={styles.fieldGroup}>
            <label style={styles.label}>Pack Name *</label>
            <input
              style={styles.input}
              type="text"
              value={packName}
              onChange={(e) => setPackName(e.target.value)}
              placeholder="My Asset Pack"
              disabled={disabled}
            />
          </div>

          <div style={styles.fieldGroup}>
            <label style={styles.label}>Tags (comma-separated)</label>
            <input
              style={styles.input}
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="environment, fantasy, props"
              disabled={disabled}
            />
          </div>

          <div style={styles.fieldGroup}>
            <label style={styles.label}>License URL</label>
            <input
              style={styles.input}
              type="url"
              value={licenseUrl}
              onChange={(e) => setLicenseUrl(e.target.value)}
              placeholder="https://..."
              disabled={disabled}
            />
          </div>
        </>
      )}

      {isMarketplace && (
        <>
          {source === 'fab' && (
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Download Strategy</label>
              <select
                style={styles.select}
                value={fabDownloadStrategy}
                onChange={(e) => setFabDownloadStrategy(e.target.value as FabDownloadStrategy)}
                disabled={disabled}
              >
                <option value="metadata_only">Metadata Only (fastest)</option>
                <option value="manifests_only">Manifests Only</option>
              </select>
            </div>
          )}

          {source === 'uas' && (
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Download Strategy</label>
              <select
                style={styles.select}
                value={uasDownloadStrategy}
                onChange={(e) => setUasDownloadStrategy(e.target.value as UasDownloadStrategy)}
                disabled={disabled}
              >
                <option value="metadata_only">Metadata Only (fastest)</option>
                <option value="manifests_only">Manifests Only (download info)</option>
                <option value="download">Download + Decrypt</option>
                <option value="extract">Download + Decrypt + Extract</option>
              </select>
            </div>
          )}

          <div style={styles.fieldGroup}>
            <label style={styles.label}>Output Directory *</label>
            <div style={styles.pathRow}>
              <input
                style={styles.pathInput}
                type="text"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                placeholder="Select output folder for manifests..."
                readOnly
              />
              <button
                type="button"
                style={styles.browseButton}
                onClick={handleOutputBrowse}
                disabled={disabled}
              >
                Browse
              </button>
            </div>
          </div>

          <div style={styles.warningBox}>
            This will fetch ALL your purchased assets from {source === 'fab' ? 'Fab' : 'Unity Asset Store'}. This may take several minutes depending on your library size.
          </div>
        </>
      )}

      <button
        type="submit"
        style={{
          ...styles.submitButton,
          ...(canSubmit ? {} : styles.submitButtonDisabled),
        }}
        disabled={!canSubmit}
      >
        {disabled ? 'Running...' : 'Start Ingestion'}
      </button>
    </form>
  );
}
