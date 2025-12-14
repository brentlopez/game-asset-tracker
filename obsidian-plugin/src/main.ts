import { Plugin, TFile, Notice } from 'obsidian';
import { DatabaseManager } from './database';
import { DashboardView, VIEW_TYPE_DASHBOARD } from './DashboardView';
import { AssetManifest } from './types';
import { generatePackNote, generatePackFileName } from './utils';

interface AssetTrackerSettings {
	dbPath: string;
	notesFolder: string;
}

const DEFAULT_SETTINGS: AssetTrackerSettings = {
	dbPath: '.obsidian/plugins/game-asset-tracker/data.db',
	notesFolder: 'Asset Packs'
};

export default class AssetTrackerPlugin extends Plugin {
	settings: AssetTrackerSettings;
	database: DatabaseManager;

	async onload() {
		await this.loadSettings();

		// Initialize database
		this.database = new DatabaseManager(this.settings.dbPath);
		
		try {
			await this.database.initialize();
			console.log('Asset Tracker: Database initialized');
		} catch (error) {
			console.error('Asset Tracker: Failed to initialize database', error);
			new Notice('Failed to initialize Asset Tracker database');
		}

		// Register dashboard view
		this.registerView(
			VIEW_TYPE_DASHBOARD,
			(leaf) => new DashboardView(leaf, this.database)
		);

		// Add ribbon icon
		this.addRibbonIcon('database', 'Asset Tracker Dashboard', () => {
			this.activateDashboard();
		});

		// Add command to open dashboard
		this.addCommand({
			id: 'open-dashboard',
			name: 'Open Dashboard',
			callback: () => {
				this.activateDashboard();
			}
		});

		// Add command to import manifest
		this.addCommand({
			id: 'import-manifest',
			name: 'Import Manifest JSON',
			callback: () => {
				this.importManifestFromFile();
			}
		});

		console.log('Asset Tracker plugin loaded');
	}

	async onunload() {
		// Close database connection
		if (this.database) {
			await this.database.save();
			this.database.close();
		}
		console.log('Asset Tracker plugin unloaded');
	}

	async activateDashboard() {
		const { workspace } = this.app;

		let leaf = workspace.getLeavesOfType(VIEW_TYPE_DASHBOARD)[0];

		if (!leaf) {
			const rightLeaf = workspace.getRightLeaf(false);
			if (rightLeaf) {
				await rightLeaf.setViewState({
					type: VIEW_TYPE_DASHBOARD,
					active: true,
				});
				leaf = rightLeaf;
			}
		}

		if (leaf) {
			workspace.revealLeaf(leaf);
		}
	}

	async importManifestFromFile() {
		// Create a file input element
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.json';
		
		input.onchange = async (e: Event) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (!file) return;

			try {
				const text = await file.text();
				const manifest: AssetManifest = JSON.parse(text);
				
				await this.importManifest(manifest);
			} catch (error) {
				console.error('Import error:', error);
				new Notice('Failed to import manifest: ' + error.message);
			}
		};

		input.click();
	}

	async importManifest(manifest: AssetManifest): Promise<void> {
		try {
			// Step A: Import into SQLite
			await this.database.importManifest(manifest);
			console.log('Imported manifest to database:', manifest.pack_id);

			// Step B: Create/Update Markdown note
			await this.createPackNote(manifest);
			
			new Notice(`Successfully imported ${manifest.pack_name}!`);
		} catch (error) {
			console.error('Import failed:', error);
			throw error;
		}
	}

	async createPackNote(manifest: AssetManifest): Promise<void> {
		const { vault } = this.app;
		
		// Ensure the notes folder exists
		const folderPath = this.settings.notesFolder;
		const folder = vault.getAbstractFileByPath(folderPath);
		
		if (!folder) {
			await vault.createFolder(folderPath);
		}

		// Generate filename and full path
		const fileName = generatePackFileName(manifest);
		const filePath = `${folderPath}/${fileName}`;

		// Generate note content
		const content = generatePackNote(manifest);

		// Check if file exists
		const existingFile = vault.getAbstractFileByPath(filePath);

		if (existingFile instanceof TFile) {
			// Update existing file
			await vault.modify(existingFile, content);
			console.log('Updated pack note:', filePath);
		} else {
			// Create new file
			await vault.create(filePath, content);
			console.log('Created pack note:', filePath);
		}
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}
}
