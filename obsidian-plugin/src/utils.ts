import { AssetManifest } from './types';

/**
 * Generate markdown note content for an Asset Pack
 */
export function generatePackNote(manifest: AssetManifest): string {
	const frontmatter = generateFrontmatter(manifest);
	const body = generateNoteBody(manifest);
	
	return `${frontmatter}\n${body}`;
}

/**
 * Generate frontmatter for pack note
 */
function generateFrontmatter(manifest: AssetManifest): string {
	const tags = manifest.global_tags || [];
	
	return `---
pack_id: ${manifest.pack_id}
source: ${manifest.source}
tags: [${tags.join(', ')}]
---`;
}

/**
 * Generate note body content
 */
function generateNoteBody(manifest: AssetManifest): string {
	const assetCount = manifest.assets.length;
	
	// Count assets by type
	const typeCount = manifest.assets.reduce((acc, asset) => {
		acc[asset.file_type] = (acc[asset.file_type] || 0) + 1;
		return acc;
	}, {} as Record<string, number>);

	const typeBreakdown = Object.entries(typeCount)
		.sort(([, a], [, b]) => b - a)
		.map(([type, count]) => `- ${type}: ${count}`)
		.join('\n');

	return `
# ${manifest.pack_name}

**Root Path:** \`${manifest.root_path}\`

## Overview

${manifest.license_link ? `**License:** [View License](${manifest.license_link})\n` : ''}
**Total Assets:** ${assetCount}

## Asset Breakdown

${typeBreakdown}

## Asset View

\`\`\`asset-tracker-view
pack_id: ${manifest.pack_id}
\`\`\`

> This code block will be rendered by the Asset Tracker plugin to display a searchable view of all assets in this pack.

## Related Projects

<!-- Add wikilinks to related projects here -->
`;
}

/**
 * Sanitize pack name for use as filename
 */
export function sanitizeFileName(name: string): string {
	return name
		.replace(/[\\/:*?"<>|]/g, '-')
		.replace(/\s+/g, '-')
		.toLowerCase();
}

/**
 * Generate note filename for a pack
 */
export function generatePackFileName(manifest: AssetManifest): string {
	return `${sanitizeFileName(manifest.pack_name)}.md`;
}
