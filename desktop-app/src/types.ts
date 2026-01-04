export type SourceType = 'filesystem' | 'fab' | 'uas';
export type FabDownloadStrategy = 'metadata_only' | 'manifests_only';
export type UasDownloadStrategy = 'metadata_only' | 'manifests_only' | 'download' | 'extract';

export interface FilesystemConfig {
  source: 'filesystem';
  path: string;
  packName: string;
  tags: string[];
  licenseUrl: string | null;
}

export interface FabConfig {
  source: 'fab';
  downloadStrategy: FabDownloadStrategy;
  outputDirectory: string;
}

export interface UasConfig {
  source: 'uas';
  downloadStrategy: UasDownloadStrategy;
  outputDirectory: string;
}

export type IngestionConfig = FilesystemConfig | FabConfig | UasConfig;

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
}

export interface IngestionResult {
  success: boolean;
  manifest: string | null;
  error: string | null;
  assetCount: number;
  totalSize: number;
  manifestCount?: number;
}

export interface AppSettings {
  ingestionPath: string;
  outputDirectory: string;
  lastSource: SourceType;
}

export const DEFAULT_SETTINGS: AppSettings = {
  ingestionPath: '',
  outputDirectory: '',
  lastSource: 'filesystem',
};

export function isFilesystemConfig(config: IngestionConfig): config is FilesystemConfig {
  return config.source === 'filesystem';
}

export function isFabConfig(config: IngestionConfig): config is FabConfig {
  return config.source === 'fab';
}

export function isUasConfig(config: IngestionConfig): config is UasConfig {
  return config.source === 'uas';
}
