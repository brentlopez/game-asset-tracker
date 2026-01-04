# Desktop App (Tauri 2.0) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a macOS desktop application using Tauri 2.0 that configures and triggers the game-asset-tracker ingestion pipeline, displaying real-time output.

**Architecture:** Tauri 2.0 with React+TypeScript frontend. Rust backend handles subprocess spawning via `tauri-plugin-shell`. Frontend uses `@tauri-apps/plugin-dialog` for folder selection and `@tauri-apps/api/core` for IPC. Real-time stdout/stderr streaming via Tauri events.

**Tech Stack:**
- Tauri 2.0 (Rust backend)
- React 18 + TypeScript (frontend, consistent with obsidian-plugin)
- `tauri-plugin-shell` (subprocess execution)
- `tauri-plugin-dialog` (folder picker)
- Vite (bundler, Tauri 2.0 default)

---

## Phase 1: Project Scaffolding

### Task 1.1: Create Tauri Project

**Files:**
- Create: `desktop-app/` (entire directory)

**Step 1: Run create-tauri-app**

```bash
cd /Users/brentlopez/Projects/game-asset-tracker
npm create tauri-app@latest -- --yes desktop-app --template react-ts --manager npm
```

Expected: Creates `desktop-app/` with React+TypeScript+Vite frontend and Rust backend.

**Step 2: Verify project structure**

```bash
ls -la desktop-app/
ls -la desktop-app/src-tauri/
```

Expected: See `src/`, `src-tauri/`, `package.json`, `vite.config.ts`.

**Step 3: Commit**

```bash
git add desktop-app/
git commit -m "feat(desktop-app): scaffold Tauri 2.0 project with React+TypeScript"
```

---

### Task 1.2: Add Tauri Plugins

**Files:**
- Modify: `desktop-app/src-tauri/Cargo.toml`
- Modify: `desktop-app/src-tauri/src/lib.rs`
- Modify: `desktop-app/package.json`
- Modify: `desktop-app/src-tauri/capabilities/default.json`

**Step 1: Add Rust plugin dependencies**

In `desktop-app/src-tauri/Cargo.toml`, add to `[dependencies]`:

```toml
tauri-plugin-shell = "2"
tauri-plugin-dialog = "2"
```

**Step 2: Initialize plugins in Rust**

In `desktop-app/src-tauri/src/lib.rs`, update the builder:

```rust
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Step 3: Add frontend plugin packages**

```bash
cd desktop-app
npm install @tauri-apps/plugin-shell @tauri-apps/plugin-dialog
```

**Step 4: Configure plugin permissions**

In `desktop-app/src-tauri/capabilities/default.json`, add permissions:

```json
{
  "identifier": "default",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-spawn",
    "shell:allow-execute",
    "shell:allow-open",
    "dialog:allow-open"
  ]
}
```

**Step 5: Verify build compiles**

```bash
cd desktop-app
npm run tauri build -- --debug
```

Expected: Build succeeds (may take a few minutes first time).

**Step 6: Commit**

```bash
git add desktop-app/
git commit -m "feat(desktop-app): add shell and dialog plugins"
```

---

## Phase 2: Type Definitions

### Task 2.1: Create Shared Types

**Files:**
- Create: `desktop-app/src/types.ts`

**Step 1: Write type definitions**

Create `desktop-app/src/types.ts`:

```typescript
// Types matching the strict JSON schema from schemas/manifest.schema.json
// Consistent with obsidian-plugin/src/types.ts

export interface AssetManifest {
  pack_id: string;
  pack_name: string;
  root_path: string;
  source: string;
  license_link?: string;
  global_tags?: string[];
  assets: AssetFile[];
}

export interface AssetFile {
  relative_path: string;
  file_type: string;
  size_bytes: number;
  metadata?: Record<string, string>;
  local_tags?: string[];
}

// Ingestion configuration
export interface IngestionConfig {
  path: string;
  name: string;
  source: string;
  tags: string[];
  license?: string;
}

// Ingestion state
export type IngestionStatus = 'idle' | 'running' | 'success' | 'error';

export interface IngestionState {
  status: IngestionStatus;
  logs: LogEntry[];
  manifest?: AssetManifest;
  error?: string;
}

export interface LogEntry {
  timestamp: Date;
  type: 'stdout' | 'stderr' | 'info';
  message: string;
}

// Source types (extensible for fab/uas later)
export type SourceType = 'filesystem' | 'fab' | 'uas';

export interface SourceConfig {
  type: SourceType;
  label: string;
  available: boolean;
}

export const AVAILABLE_SOURCES: SourceConfig[] = [
  { type: 'filesystem', label: 'Local Filesystem', available: true },
  { type: 'fab', label: 'Fab Marketplace', available: false },
  { type: 'uas', label: 'Unity Asset Store', available: false },
];

// App settings
export interface AppSettings {
  ingestionPath: string;  // Path to ingestion directory (where uv is)
  outputDirectory: string; // Where to save manifests
}

export const DEFAULT_SETTINGS: AppSettings = {
  ingestionPath: '',
  outputDirectory: '',
};
```

**Step 2: Commit**

```bash
git add desktop-app/src/types.ts
git commit -m "feat(desktop-app): add shared TypeScript types"
```

---

## Phase 3: Rust Backend Commands

### Task 3.1: Create Ingestion Command

**Files:**
- Modify: `desktop-app/src-tauri/src/lib.rs`

**Step 1: Add command module**

Replace `desktop-app/src-tauri/src/lib.rs` with:

```rust
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct IngestionConfig {
    path: String,
    name: String,
    source: String,
    tags: Vec<String>,
    license: Option<String>,
}

#[derive(Debug, Serialize, Clone)]
pub struct LogEntry {
    #[serde(rename = "type")]
    log_type: String,
    message: String,
}

#[derive(Debug, Serialize, Clone)]
pub struct IngestionResult {
    success: bool,
    manifest_json: Option<String>,
    error: Option<String>,
}

#[tauri::command]
async fn run_ingestion(
    app: AppHandle,
    config: IngestionConfig,
    ingestion_path: String,
) -> Result<IngestionResult, String> {
    // Build CLI arguments
    let mut args = vec![
        "run".to_string(),
        "ingest".to_string(),
        "--path".to_string(),
        config.path.clone(),
        "--name".to_string(),
        config.name.clone(),
        "--source".to_string(),
        config.source.clone(),
    ];

    // Add tags if present
    if !config.tags.is_empty() {
        args.push("--tags".to_string());
        args.extend(config.tags.iter().cloned());
    }

    // Add license if present
    if let Some(license) = &config.license {
        if !license.is_empty() {
            args.push("--license".to_string());
            args.push(license.clone());
        }
    }

    // Spawn uv process
    let shell = app.shell();
    let command = shell
        .command("uv")
        .args(&args)
        .current_dir(&ingestion_path);

    let (mut rx, _child) = command.spawn().map_err(|e| format!("Failed to spawn: {}", e))?;

    let mut stdout_buffer = String::new();
    let mut stderr_buffer = String::new();

    // Process events
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(line) => {
                let text = String::from_utf8_lossy(&line).to_string();
                stdout_buffer.push_str(&text);
                // Emit for real-time display (stdout is the manifest JSON)
            }
            CommandEvent::Stderr(line) => {
                let text = String::from_utf8_lossy(&line).to_string();
                stderr_buffer.push_str(&text);
                stderr_buffer.push('\n');
                // Emit log event for real-time display
                let _ = app.emit(
                    "ingestion-log",
                    LogEntry {
                        log_type: "stderr".to_string(),
                        message: text,
                    },
                );
            }
            CommandEvent::Terminated(status) => {
                if status.success() {
                    return Ok(IngestionResult {
                        success: true,
                        manifest_json: Some(stdout_buffer),
                        error: None,
                    });
                } else {
                    return Ok(IngestionResult {
                        success: false,
                        manifest_json: None,
                        error: Some(stderr_buffer),
                    });
                }
            }
            CommandEvent::Error(err) => {
                return Err(format!("Command error: {}", err));
            }
            _ => {}
        }
    }

    Err("Process ended unexpectedly".to_string())
}

#[tauri::command]
fn validate_ingestion_path(path: String) -> Result<bool, String> {
    let pyproject = std::path::Path::new(&path).join("pyproject.toml");
    Ok(pyproject.exists())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![run_ingestion, validate_ingestion_path])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Step 2: Build and verify**

```bash
cd desktop-app
npm run tauri build -- --debug
```

Expected: Build succeeds.

**Step 3: Commit**

```bash
git add desktop-app/src-tauri/
git commit -m "feat(desktop-app): add Rust ingestion command with real-time output"
```

---

## Phase 4: React Components

### Task 4.1: Create IngestionForm Component

**Files:**
- Create: `desktop-app/src/components/IngestionForm.tsx`

**Step 1: Write the component**

Create `desktop-app/src/components/IngestionForm.tsx`:

```typescript
import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { IngestionConfig, AVAILABLE_SOURCES, SourceType } from '../types';

interface IngestionFormProps {
  onSubmit: (config: IngestionConfig) => void;
  disabled: boolean;
}

export function IngestionForm({ onSubmit, disabled }: IngestionFormProps) {
  const [path, setPath] = useState('');
  const [name, setName] = useState('');
  const [source, setSource] = useState<SourceType>('filesystem');
  const [tagsInput, setTagsInput] = useState('');
  const [license, setLicense] = useState('');

  const handleSelectFolder = async () => {
    const selected = await open({
      title: 'Select Asset Pack Folder',
      directory: true,
    });
    if (selected) {
      setPath(selected);
      // Auto-fill name from folder name if empty
      if (!name) {
        const folderName = selected.split('/').pop() || '';
        setName(folderName);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!path || !name || !source) return;

    const tags = tagsInput
      .split(/[\s,]+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    onSubmit({
      path,
      name,
      source,
      tags,
      license: license || undefined,
    });
  };

  const isValid = path && name && source;

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <h3 style={styles.sectionTitle}>Ingestion Configuration</h3>

      {/* Source Type */}
      <div style={styles.field}>
        <label style={styles.label}>Source Type</label>
        <select
          value={source}
          onChange={(e) => setSource(e.target.value as SourceType)}
          disabled={disabled}
          style={styles.select}
        >
          {AVAILABLE_SOURCES.map((s) => (
            <option key={s.type} value={s.type} disabled={!s.available}>
              {s.label} {!s.available && '(Coming Soon)'}
            </option>
          ))}
        </select>
      </div>

      {/* Folder Path */}
      <div style={styles.field}>
        <label style={styles.label}>Asset Folder</label>
        <div style={styles.pathRow}>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/path/to/assets"
            disabled={disabled}
            style={{ ...styles.input, flex: 1 }}
          />
          <button
            type="button"
            onClick={handleSelectFolder}
            disabled={disabled}
            style={styles.browseButton}
          >
            Browse
          </button>
        </div>
      </div>

      {/* Pack Name */}
      <div style={styles.field}>
        <label style={styles.label}>Pack Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Asset Pack"
          disabled={disabled}
          style={styles.input}
        />
      </div>

      {/* Tags */}
      <div style={styles.field}>
        <label style={styles.label}>Tags (space or comma separated)</label>
        <input
          type="text"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="3d fantasy characters"
          disabled={disabled}
          style={styles.input}
        />
      </div>

      {/* License URL */}
      <div style={styles.field}>
        <label style={styles.label}>License URL (optional)</label>
        <input
          type="text"
          value={license}
          onChange={(e) => setLicense(e.target.value)}
          placeholder="https://example.com/license"
          disabled={disabled}
          style={styles.input}
        />
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={disabled || !isValid}
        style={{
          ...styles.submitButton,
          opacity: disabled || !isValid ? 0.5 : 1,
          cursor: disabled || !isValid ? 'not-allowed' : 'pointer',
        }}
      >
        {disabled ? 'Running...' : 'Run Ingestion'}
      </button>
    </form>
  );
}

const styles: Record<string, React.CSSProperties> = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  sectionTitle: {
    margin: '0 0 8px 0',
    fontSize: '18px',
    fontWeight: 600,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#666',
  },
  input: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    outline: 'none',
  },
  select: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    outline: 'none',
    backgroundColor: 'white',
  },
  pathRow: {
    display: 'flex',
    gap: '8px',
  },
  browseButton: {
    padding: '10px 16px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    backgroundColor: '#f5f5f5',
    cursor: 'pointer',
  },
  submitButton: {
    marginTop: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 600,
    color: 'white',
    backgroundColor: '#007AFF',
    border: 'none',
    borderRadius: '8px',
  },
};
```

**Step 2: Commit**

```bash
git add desktop-app/src/components/
git commit -m "feat(desktop-app): add IngestionForm component with folder picker"
```

---

### Task 4.2: Create LogViewer Component

**Files:**
- Create: `desktop-app/src/components/LogViewer.tsx`

**Step 1: Write the component**

Create `desktop-app/src/components/LogViewer.tsx`:

```typescript
import { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

interface LogViewerProps {
  logs: LogEntry[];
  autoScroll?: boolean;
}

export function LogViewer({ logs, autoScroll = true }: LogViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Output Log</h3>
      <div ref={containerRef} style={styles.logContainer}>
        {logs.length === 0 ? (
          <div style={styles.placeholder}>Logs will appear here...</div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              style={{
                ...styles.logEntry,
                color: log.type === 'stderr' ? '#666' : log.type === 'info' ? '#007AFF' : '#333',
              }}
            >
              <span style={styles.timestamp}>
                {log.timestamp.toLocaleTimeString()}
              </span>
              <span style={styles.message}>{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  title: {
    margin: '0 0 12px 0',
    fontSize: '18px',
    fontWeight: 600,
  },
  logContainer: {
    flex: 1,
    minHeight: '200px',
    maxHeight: '400px',
    overflowY: 'auto',
    padding: '12px',
    backgroundColor: '#1e1e1e',
    borderRadius: '8px',
    fontFamily: 'Monaco, Menlo, "Courier New", monospace',
    fontSize: '12px',
  },
  placeholder: {
    color: '#666',
    fontStyle: 'italic',
  },
  logEntry: {
    display: 'flex',
    gap: '12px',
    lineHeight: 1.5,
  },
  timestamp: {
    color: '#666',
    flexShrink: 0,
  },
  message: {
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
};
```

**Step 2: Commit**

```bash
git add desktop-app/src/components/LogViewer.tsx
git commit -m "feat(desktop-app): add LogViewer component with auto-scroll"
```

---

### Task 4.3: Create ResultView Component

**Files:**
- Create: `desktop-app/src/components/ResultView.tsx`

**Step 1: Write the component**

Create `desktop-app/src/components/ResultView.tsx`:

```typescript
import { AssetManifest, IngestionStatus } from '../types';

interface ResultViewProps {
  status: IngestionStatus;
  manifest?: AssetManifest;
  error?: string;
  onOpenFile?: () => void;
  onReset: () => void;
}

export function ResultView({ status, manifest, error, onOpenFile, onReset }: ResultViewProps) {
  if (status === 'idle' || status === 'running') {
    return null;
  }

  return (
    <div style={styles.container}>
      {status === 'success' && manifest && (
        <>
          <div style={styles.successBanner}>
            <span style={styles.successIcon}>✓</span>
            <span>Ingestion Complete</span>
          </div>
          <div style={styles.stats}>
            <StatItem label="Pack Name" value={manifest.pack_name} />
            <StatItem label="Assets Found" value={manifest.assets.length.toString()} />
            <StatItem label="Pack ID" value={manifest.pack_id.slice(0, 8) + '...'} />
            {manifest.global_tags && manifest.global_tags.length > 0 && (
              <StatItem label="Tags" value={manifest.global_tags.join(', ')} />
            )}
          </div>
          <div style={styles.actions}>
            {onOpenFile && (
              <button onClick={onOpenFile} style={styles.secondaryButton}>
                Open Manifest
              </button>
            )}
            <button onClick={onReset} style={styles.primaryButton}>
              New Ingestion
            </button>
          </div>
        </>
      )}

      {status === 'error' && (
        <>
          <div style={styles.errorBanner}>
            <span style={styles.errorIcon}>✗</span>
            <span>Ingestion Failed</span>
          </div>
          <div style={styles.errorMessage}>
            <pre>{error}</pre>
          </div>
          <div style={styles.actions}>
            <button onClick={onReset} style={styles.primaryButton}>
              Try Again
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div style={styles.statItem}>
      <span style={styles.statLabel}>{label}</span>
      <span style={styles.statValue}>{value}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '24px',
  },
  successBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#d4edda',
    color: '#155724',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 600,
  },
  successIcon: {
    fontSize: '20px',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 600,
  },
  errorIcon: {
    fontSize: '20px',
  },
  stats: {
    marginTop: '16px',
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
  },
  statItem: {
    padding: '12px',
    backgroundColor: '#f5f5f5',
    borderRadius: '6px',
  },
  statLabel: {
    display: 'block',
    fontSize: '12px',
    color: '#666',
    marginBottom: '4px',
  },
  statValue: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
  },
  errorMessage: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: '#f5f5f5',
    borderRadius: '6px',
    fontFamily: 'Monaco, Menlo, "Courier New", monospace',
    fontSize: '12px',
    overflow: 'auto',
    maxHeight: '200px',
  },
  actions: {
    marginTop: '16px',
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
  },
  primaryButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'white',
    backgroundColor: '#007AFF',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  secondaryButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
    color: '#333',
    backgroundColor: '#e0e0e0',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
};
```

**Step 2: Commit**

```bash
git add desktop-app/src/components/ResultView.tsx
git commit -m "feat(desktop-app): add ResultView component with stats display"
```

---

### Task 4.4: Create Settings Component

**Files:**
- Create: `desktop-app/src/components/Settings.tsx`

**Step 1: Write the component**

Create `desktop-app/src/components/Settings.tsx`:

```typescript
import { useState, useEffect } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke } from '@tauri-apps/api/core';
import { AppSettings } from '../types';

interface SettingsProps {
  settings: AppSettings;
  onSave: (settings: AppSettings) => void;
  onClose: () => void;
}

export function Settings({ settings, onSave, onClose }: SettingsProps) {
  const [ingestionPath, setIngestionPath] = useState(settings.ingestionPath);
  const [outputDirectory, setOutputDirectory] = useState(settings.outputDirectory);
  const [pathValid, setPathValid] = useState<boolean | null>(null);

  useEffect(() => {
    if (ingestionPath) {
      validatePath(ingestionPath);
    }
  }, [ingestionPath]);

  const validatePath = async (path: string) => {
    try {
      const valid = await invoke<boolean>('validate_ingestion_path', { path });
      setPathValid(valid);
    } catch {
      setPathValid(false);
    }
  };

  const handleSelectIngestionPath = async () => {
    const selected = await open({
      title: 'Select Ingestion Directory',
      directory: true,
    });
    if (selected) {
      setIngestionPath(selected);
    }
  };

  const handleSelectOutputDirectory = async () => {
    const selected = await open({
      title: 'Select Output Directory',
      directory: true,
    });
    if (selected) {
      setOutputDirectory(selected);
    }
  };

  const handleSave = () => {
    onSave({
      ingestionPath,
      outputDirectory,
    });
    onClose();
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h2 style={styles.title}>Settings</h2>

        <div style={styles.field}>
          <label style={styles.label}>Ingestion Directory</label>
          <p style={styles.hint}>
            Path to the game-asset-tracker/ingestion directory containing pyproject.toml
          </p>
          <div style={styles.pathRow}>
            <input
              type="text"
              value={ingestionPath}
              onChange={(e) => setIngestionPath(e.target.value)}
              placeholder="/path/to/game-asset-tracker/ingestion"
              style={{
                ...styles.input,
                flex: 1,
                borderColor: pathValid === false ? '#dc3545' : pathValid === true ? '#28a745' : '#ddd',
              }}
            />
            <button onClick={handleSelectIngestionPath} style={styles.browseButton}>
              Browse
            </button>
          </div>
          {pathValid === false && (
            <span style={styles.error}>pyproject.toml not found in this directory</span>
          )}
          {pathValid === true && (
            <span style={styles.success}>Valid ingestion directory</span>
          )}
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Output Directory</label>
          <p style={styles.hint}>Where to save generated manifest files</p>
          <div style={styles.pathRow}>
            <input
              type="text"
              value={outputDirectory}
              onChange={(e) => setOutputDirectory(e.target.value)}
              placeholder="/path/to/output"
              style={{ ...styles.input, flex: 1 }}
            />
            <button onClick={handleSelectOutputDirectory} style={styles.browseButton}>
              Browse
            </button>
          </div>
        </div>

        <div style={styles.actions}>
          <button onClick={onClose} style={styles.cancelButton}>
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!pathValid}
            style={{
              ...styles.saveButton,
              opacity: pathValid ? 1 : 0.5,
              cursor: pathValid ? 'pointer' : 'not-allowed',
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '24px',
    width: '500px',
    maxWidth: '90vw',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
  },
  title: {
    margin: '0 0 20px 0',
    fontSize: '20px',
    fontWeight: 600,
  },
  field: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '4px',
  },
  hint: {
    fontSize: '12px',
    color: '#666',
    margin: '0 0 8px 0',
  },
  input: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    outline: 'none',
  },
  pathRow: {
    display: 'flex',
    gap: '8px',
  },
  browseButton: {
    padding: '10px 16px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    backgroundColor: '#f5f5f5',
    cursor: 'pointer',
  },
  error: {
    display: 'block',
    marginTop: '4px',
    fontSize: '12px',
    color: '#dc3545',
  },
  success: {
    display: 'block',
    marginTop: '4px',
    fontSize: '12px',
    color: '#28a745',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
    marginTop: '24px',
  },
  cancelButton: {
    padding: '10px 20px',
    fontSize: '14px',
    color: '#333',
    backgroundColor: '#e0e0e0',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  saveButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'white',
    backgroundColor: '#007AFF',
    border: 'none',
    borderRadius: '6px',
  },
};
```

**Step 2: Commit**

```bash
git add desktop-app/src/components/Settings.tsx
git commit -m "feat(desktop-app): add Settings component with path validation"
```

---

## Phase 5: Main App Integration

### Task 5.1: Create Main App Component

**Files:**
- Modify: `desktop-app/src/App.tsx`
- Create: `desktop-app/src/App.css`

**Step 1: Write the main App component**

Replace `desktop-app/src/App.tsx` with:

```typescript
import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { IngestionForm } from './components/IngestionForm';
import { LogViewer } from './components/LogViewer';
import { ResultView } from './components/ResultView';
import { Settings } from './components/Settings';
import {
  IngestionConfig,
  IngestionState,
  AppSettings,
  DEFAULT_SETTINGS,
  AssetManifest,
  LogEntry,
} from './types';
import './App.css';

interface IngestionResult {
  success: boolean;
  manifest_json?: string;
  error?: string;
}

function App() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [showSettings, setShowSettings] = useState(false);
  const [state, setState] = useState<IngestionState>({
    status: 'idle',
    logs: [],
  });

  // Load settings from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('app-settings');
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Listen for log events from Rust backend
  useEffect(() => {
    const unlisten = listen<{ type: string; message: string }>('ingestion-log', (event) => {
      const entry: LogEntry = {
        timestamp: new Date(),
        type: event.payload.type as 'stdout' | 'stderr' | 'info',
        message: event.payload.message,
      };
      setState((prev) => ({
        ...prev,
        logs: [...prev.logs, entry],
      }));
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const handleSaveSettings = (newSettings: AppSettings) => {
    setSettings(newSettings);
    localStorage.setItem('app-settings', JSON.stringify(newSettings));
  };

  const handleRunIngestion = async (config: IngestionConfig) => {
    if (!settings.ingestionPath) {
      setShowSettings(true);
      return;
    }

    // Reset state
    setState({
      status: 'running',
      logs: [
        {
          timestamp: new Date(),
          type: 'info',
          message: `Starting ingestion for "${config.name}"...`,
        },
      ],
    });

    try {
      const result = await invoke<IngestionResult>('run_ingestion', {
        config,
        ingestionPath: settings.ingestionPath,
      });

      if (result.success && result.manifest_json) {
        const manifest: AssetManifest = JSON.parse(result.manifest_json);

        // Save manifest to output directory if configured
        if (settings.outputDirectory) {
          // TODO: Save file using Tauri fs plugin
        }

        setState((prev) => ({
          ...prev,
          status: 'success',
          manifest,
          logs: [
            ...prev.logs,
            {
              timestamp: new Date(),
              type: 'info',
              message: `Successfully processed ${manifest.assets.length} assets.`,
            },
          ],
        }));
      } else {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: result.error || 'Unknown error',
        }));
      }
    } catch (error) {
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
        logs: [
          ...prev.logs,
          {
            timestamp: new Date(),
            type: 'stderr',
            message: `Error: ${error}`,
          },
        ],
      }));
    }
  };

  const handleReset = () => {
    setState({
      status: 'idle',
      logs: [],
    });
  };

  const needsSetup = !settings.ingestionPath;

  return (
    <div className="app">
      <header className="header">
        <h1>Game Asset Tracker</h1>
        <button className="settings-button" onClick={() => setShowSettings(true)}>
          Settings
        </button>
      </header>

      <main className="main">
        {needsSetup && (
          <div className="setup-banner">
            <p>Please configure the ingestion directory path in Settings to get started.</p>
            <button onClick={() => setShowSettings(true)}>Open Settings</button>
          </div>
        )}

        <div className="content">
          <div className="form-section">
            <IngestionForm
              onSubmit={handleRunIngestion}
              disabled={state.status === 'running' || needsSetup}
            />
          </div>

          <div className="output-section">
            <LogViewer logs={state.logs} />
            <ResultView
              status={state.status}
              manifest={state.manifest}
              error={state.error}
              onReset={handleReset}
            />
          </div>
        </div>
      </main>

      {showSettings && (
        <Settings
          settings={settings}
          onSave={handleSaveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}

export default App;
```

**Step 2: Create App.css**

Create `desktop-app/src/App.css`:

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background-color: #f5f5f5;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background-color: white;
  border-bottom: 1px solid #e0e0e0;
}

.header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.settings-button {
  padding: 8px 16px;
  font-size: 14px;
  color: #333;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
}

.settings-button:hover {
  background-color: #e5e5e5;
}

.main {
  flex: 1;
  padding: 24px;
}

.setup-banner {
  padding: 16px;
  margin-bottom: 24px;
  background-color: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setup-banner p {
  margin: 0;
  color: #856404;
}

.setup-banner button {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: white;
  background-color: #007AFF;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.form-section,
.output-section {
  background-color: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

@media (max-width: 900px) {
  .content {
    grid-template-columns: 1fr;
  }
}
```

**Step 3: Clean up default files**

```bash
rm desktop-app/src/assets/react.svg 2>/dev/null || true
rm desktop-app/public/tauri.svg 2>/dev/null || true
```

**Step 4: Build and test**

```bash
cd desktop-app
npm run tauri dev
```

Expected: App launches with form on left, log viewer on right, settings modal works.

**Step 5: Commit**

```bash
git add desktop-app/src/
git commit -m "feat(desktop-app): integrate main App with all components"
```

---

## Phase 6: Polish & Documentation

### Task 6.1: Add Component Index

**Files:**
- Create: `desktop-app/src/components/index.ts`

**Step 1: Create barrel export**

Create `desktop-app/src/components/index.ts`:

```typescript
export { IngestionForm } from './IngestionForm';
export { LogViewer } from './LogViewer';
export { ResultView } from './ResultView';
export { Settings } from './Settings';
```

**Step 2: Commit**

```bash
git add desktop-app/src/components/index.ts
git commit -m "chore(desktop-app): add component barrel export"
```

---

### Task 6.2: Update App Metadata

**Files:**
- Modify: `desktop-app/src-tauri/tauri.conf.json`

**Step 1: Update Tauri config**

In `desktop-app/src-tauri/tauri.conf.json`, update:

```json
{
  "$schema": "../node_modules/@tauri-apps/cli/config.schema.json",
  "productName": "Game Asset Tracker",
  "identifier": "dev.brentlopez.game-asset-tracker",
  "version": "0.1.0",
  "build": {
    "beforeBuildCommand": "npm run build",
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:1420",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "Game Asset Tracker",
        "width": 1200,
        "height": 800,
        "minWidth": 800,
        "minHeight": 600,
        "resizable": true
      }
    ]
  },
  "bundle": {
    "active": true,
    "category": "DeveloperTool",
    "copyright": "Copyright 2026 Brent Lopez",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "macOS": {
      "minimumSystemVersion": "10.15"
    }
  }
}
```

**Step 2: Commit**

```bash
git add desktop-app/src-tauri/tauri.conf.json
git commit -m "chore(desktop-app): update app metadata and window config"
```

---

### Task 6.3: Create README

**Files:**
- Create: `desktop-app/README.md`

**Step 1: Write README**

Create `desktop-app/README.md`:

```markdown
# Game Asset Tracker - Desktop App

A macOS desktop application for configuring and running the game-asset-tracker ingestion pipeline.

## Features

- **Source Selection**: Choose filesystem source (fab/uas coming soon)
- **Folder Picker**: Native macOS folder selection dialog
- **Real-time Logs**: Watch ingestion progress as it happens
- **Manifest Preview**: View asset count and pack details after ingestion
- **Configurable Paths**: Set ingestion and output directories

## Development

### Prerequisites

- [Rust](https://rustup.rs/) (latest stable)
- [Node.js](https://nodejs.org/) 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
# Install dependencies
npm install

# Run in development mode
npm run tauri dev

# Build for production
npm run tauri build
```

### Configuration

On first launch, open Settings and configure:

1. **Ingestion Directory**: Path to `game-asset-tracker/ingestion/` (must contain `pyproject.toml`)
2. **Output Directory**: Where to save generated manifest JSON files

## Architecture

```
desktop-app/
├── src/                    # React frontend
│   ├── components/
│   │   ├── IngestionForm.tsx  # Configuration form
│   │   ├── LogViewer.tsx      # Real-time output display
│   │   ├── ResultView.tsx     # Success/error results
│   │   └── Settings.tsx       # App configuration
│   ├── App.tsx             # Main app component
│   └── types.ts            # Shared TypeScript types
├── src-tauri/              # Rust backend
│   ├── src/
│   │   └── lib.rs          # Tauri commands
│   ├── Cargo.toml
│   └── tauri.conf.json
└── package.json
```

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite
- **Backend**: Tauri 2.0, Rust
- **Plugins**: tauri-plugin-shell (subprocess), tauri-plugin-dialog (file picker)

## Future Enhancements

- [ ] Fab marketplace source integration
- [ ] Unity Asset Store source integration
- [ ] Batch ingestion mode
- [ ] Manifest file saving
- [ ] Integration with Obsidian plugin
```

**Step 2: Commit**

```bash
git add desktop-app/README.md
git commit -m "docs(desktop-app): add README with setup instructions"
```

---

### Task 6.4: Create AGENTS.md

**Files:**
- Create: `desktop-app/AGENTS.md`

**Step 1: Write AGENTS.md**

Create `desktop-app/AGENTS.md`:

```markdown
# DESKTOP APP KNOWLEDGE BASE

**Scope:** Tauri 2.0 macOS app for ingestion pipeline configuration

## OVERVIEW

React+TypeScript frontend with Rust backend. Spawns `uv run ingest` subprocess, streams output via events.

## STRUCTURE

```
src/
├── components/
│   ├── IngestionForm.tsx   # Config form with folder picker
│   ├── LogViewer.tsx       # Real-time log display
│   ├── ResultView.tsx      # Success/error state
│   └── Settings.tsx        # App configuration modal
├── App.tsx                 # Main component, state management
├── App.css                 # Global styles
└── types.ts                # Shared types (mirrors obsidian-plugin)

src-tauri/
├── src/lib.rs              # Tauri commands, subprocess handling
├── Cargo.toml              # Rust dependencies
├── tauri.conf.json         # App config, window settings
└── capabilities/default.json # Plugin permissions
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add new source type | `src/types.ts` (SourceConfig), `src/components/IngestionForm.tsx` |
| Modify CLI arguments | `src-tauri/src/lib.rs` (run_ingestion) |
| Change UI layout | `src/App.tsx`, `src/App.css` |
| Add new settings | `src/types.ts` (AppSettings), `src/components/Settings.tsx` |
| Plugin permissions | `src-tauri/capabilities/default.json` |

## CONVENTIONS

- **Types consistent** with obsidian-plugin/src/types.ts
- **Inline styles** for component-specific styling (matches obsidian-plugin pattern)
- **localStorage** for settings persistence
- **Tauri events** for real-time subprocess output streaming

## COMMANDS

```bash
npm install             # Install dependencies
npm run tauri dev       # Development mode with hot reload
npm run tauri build     # Production build (.app bundle)
```

## IPC PATTERN

```typescript
// Frontend → Backend
const result = await invoke<IngestionResult>('run_ingestion', { config, ingestionPath });

// Backend → Frontend (events)
app.emit("ingestion-log", LogEntry { ... });

// Frontend listener
listen<LogEntry>('ingestion-log', (event) => { ... });
```

## ANTI-PATTERNS

| NEVER | Instead |
|-------|---------|
| Direct subprocess from frontend | Use Rust command via invoke |
| Block UI during ingestion | Use async + event streaming |
| Hardcode paths | Use Settings component |
| Skip path validation | Use validate_ingestion_path command |
```

**Step 2: Commit**

```bash
git add desktop-app/AGENTS.md
git commit -m "docs(desktop-app): add AGENTS.md knowledge base"
```

---

## Phase 7: Final Verification

### Task 7.1: Full Build and Test

**Files:** None (verification only)

**Step 1: Clean build**

```bash
cd desktop-app
rm -rf node_modules dist target 2>/dev/null || true
npm install
npm run tauri build
```

Expected: Build completes, creates `target/release/bundle/macos/Game Asset Tracker.app`

**Step 2: Test the built app**

```bash
open "desktop-app/src-tauri/target/release/bundle/macos/Game Asset Tracker.app"
```

Expected: App launches, settings modal appears on first run.

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(desktop-app): complete MVP implementation"
```

---

## Summary

This plan creates a fully functional macOS desktop app with:

1. **Project scaffolding** - Tauri 2.0 + React + TypeScript
2. **Plugins** - shell (subprocess), dialog (folder picker)
3. **Rust backend** - `run_ingestion` command with event streaming
4. **React frontend** - Form, log viewer, result display, settings
5. **Documentation** - README and AGENTS.md

**Future work** (not in this plan):
- Fab/UAS source integration (requires auth UI)
- Manifest file saving via tauri-plugin-fs
- Integration with Obsidian plugin
