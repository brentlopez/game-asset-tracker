import initSqlJs, { Database } from 'sql.js';
import { AssetManifest, PackRecord, AssetRecord } from './types';

export class DatabaseManager {
	private db: Database | null = null;
	private dbPath: string;
	private sqlJs: any = null;

	constructor(dbPath: string) {
		this.dbPath = dbPath;
	}

	async initialize(): Promise<void> {
		// Initialize sql.js with WASM file
		this.sqlJs = await initSqlJs({
			locateFile: (file: string) => {
				// This will be bundled by esbuild
				return `https://sql.js.org/dist/${file}`;
			}
		});

		// Try to load existing database
		await this.load();
		
		// Create schema if it doesn't exist
		this.createSchema();
	}

	private createSchema(): void {
		if (!this.db) return;

		// Create packs table
		this.db.run(`
			CREATE TABLE IF NOT EXISTS packs (
				pack_id TEXT PRIMARY KEY,
				pack_name TEXT NOT NULL,
				root_path TEXT NOT NULL,
				source TEXT,
				license_link TEXT,
				global_tags TEXT,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		`);

		// Create assets table
		this.db.run(`
			CREATE TABLE IF NOT EXISTS assets (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				pack_id TEXT NOT NULL,
				relative_path TEXT NOT NULL,
				file_type TEXT NOT NULL,
				size_bytes INTEGER NOT NULL,
				metadata_json TEXT,
				local_tags TEXT,
				FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
			)
		`);

		// Create indexes
		this.db.run('CREATE INDEX IF NOT EXISTS idx_file_type ON assets(file_type)');
		this.db.run('CREATE INDEX IF NOT EXISTS idx_pack_id ON assets(pack_id)');
		this.db.run('CREATE INDEX IF NOT EXISTS idx_local_tags ON assets(local_tags)');
	}

	async load(): Promise<void> {
		try {
			// Try to read existing database file
			const data = await this.readFile(this.dbPath);
			if (data) {
				this.db = new this.sqlJs.Database(data);
			} else {
				// Create new database
				this.db = new this.sqlJs.Database();
			}
		} catch (error) {
			console.error('Error loading database:', error);
			// Create new database if load fails
			this.db = new this.sqlJs.Database();
		}
	}

	async save(): Promise<void> {
		if (!this.db) return;
		
		const data = this.db.export();
		await this.writeFile(this.dbPath, data);
	}

	private async readFile(path: string): Promise<Uint8Array | null> {
		// Use Obsidian's file system API
		try {
			const adapter = (window as any).app?.vault?.adapter;
			if (!adapter) return null;

			const exists = await adapter.exists(path);
			if (!exists) return null;

			const arrayBuffer = await adapter.readBinary(path);
			return new Uint8Array(arrayBuffer);
		} catch (error) {
			console.error('Error reading file:', error);
			return null;
		}
	}

	private async writeFile(path: string, data: Uint8Array): Promise<void> {
		try {
			const adapter = (window as any).app?.vault?.adapter;
			if (!adapter) return;

			await adapter.writeBinary(path, data);
		} catch (error) {
			console.error('Error writing file:', error);
		}
	}

	/**
	 * Import a manifest JSON into the database
	 */
	async importManifest(manifest: AssetManifest): Promise<void> {
		if (!this.db) throw new Error('Database not initialized');

		// Check if pack already exists
		const existingPack = this.db.exec(
			'SELECT pack_id FROM packs WHERE pack_id = ?',
			[manifest.pack_id]
		);

		if (existingPack.length > 0) {
			// Update existing pack
			this.db.run(
				`UPDATE packs SET 
					pack_name = ?, 
					root_path = ?, 
					source = ?, 
					license_link = ?, 
					global_tags = ?,
					updated_at = CURRENT_TIMESTAMP
				WHERE pack_id = ?`,
				[
					manifest.pack_name,
					manifest.root_path,
					manifest.source,
					manifest.license_link || null,
					manifest.global_tags ? JSON.stringify(manifest.global_tags) : null,
					manifest.pack_id
				]
			);

			// Delete old assets
			this.db.run('DELETE FROM assets WHERE pack_id = ?', [manifest.pack_id]);
		} else {
			// Insert new pack
			this.db.run(
				`INSERT INTO packs (pack_id, pack_name, root_path, source, license_link, global_tags)
				VALUES (?, ?, ?, ?, ?, ?)`,
				[
					manifest.pack_id,
					manifest.pack_name,
					manifest.root_path,
					manifest.source,
					manifest.license_link || null,
					manifest.global_tags ? JSON.stringify(manifest.global_tags) : null
				]
			);
		}

		// Insert assets
		const stmt = this.db.prepare(
			`INSERT INTO assets (pack_id, relative_path, file_type, size_bytes, metadata_json, local_tags)
			VALUES (?, ?, ?, ?, ?, ?)`
		);

		for (const asset of manifest.assets) {
			stmt.run([
				manifest.pack_id,
				asset.relative_path,
				asset.file_type,
				asset.size_bytes,
				asset.metadata ? JSON.stringify(asset.metadata) : null,
				asset.local_tags ? JSON.stringify(asset.local_tags) : null
			]);
		}

		stmt.free();
		await this.save();
	}

	/**
	 * Query the database
	 */
	query(sql: string, params: any[] = []): any[] {
		if (!this.db) throw new Error('Database not initialized');

		const result = this.db.exec(sql, params);
		if (result.length === 0) return [];

		// Convert result to array of objects
		const columns = result[0].columns;
		const values = result[0].values;

		return values.map(row => {
			const obj: any = {};
			columns.forEach((col, i) => {
				obj[col] = row[i];
			});
			return obj;
		});
	}

	/**
	 * Get pack by ID
	 */
	getPack(packId: string): PackRecord | null {
		const results = this.query('SELECT * FROM packs WHERE pack_id = ?', [packId]);
		return results.length > 0 ? results[0] : null;
	}

	/**
	 * Get all packs
	 */
	getAllPacks(): PackRecord[] {
		return this.query('SELECT * FROM packs ORDER BY pack_name');
	}

	/**
	 * Get assets for a pack
	 */
	getAssetsByPack(packId: string): AssetRecord[] {
		return this.query('SELECT * FROM assets WHERE pack_id = ?', [packId]);
	}

	/**
	 * Get asset count
	 */
	getAssetCount(): number {
		const result = this.query('SELECT COUNT(*) as count FROM assets');
		return result.length > 0 ? result[0].count : 0;
	}

	close(): void {
		if (this.db) {
			this.db.close();
			this.db = null;
		}
	}
}
