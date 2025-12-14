// Types matching the strict JSON schema from ARCHITECTURE.md

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

export interface PackRecord {
	pack_id: string;
	pack_name: string;
	root_path: string;
	source: string;
	license_link?: string;
	global_tags?: string;
	created_at?: string;
	updated_at?: string;
}

export interface AssetRecord {
	id?: number;
	pack_id: string;
	relative_path: string;
	file_type: string;
	size_bytes: number;
	metadata_json?: string;
	local_tags?: string;
}
