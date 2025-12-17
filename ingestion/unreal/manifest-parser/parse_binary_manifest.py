#!/usr/bin/env python3
"""
Epic Games Binary Manifest Parser
Extracts structured JSON data from Epic's binary manifest format
"""

import struct
import json
import sys
from pathlib import Path


class BinaryManifestParser:
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.data = None
        self.offset = 0
        self.manifest = {}
        
    def read_bytes(self, count):
        """Read count bytes and advance offset"""
        result = self.data[self.offset:self.offset + count]
        self.offset += count
        return result
    
    def read_uint32(self):
        """Read a 32-bit unsigned integer (little-endian)"""
        return struct.unpack('<I', self.read_bytes(4))[0]
    
    def read_uint64(self):
        """Read a 64-bit unsigned integer (little-endian)"""
        return struct.unpack('<Q', self.read_bytes(8))[0]
    
    def read_string(self):
        """Read a length-prefixed string"""
        # String format: 4-byte length, then UTF-8 bytes, then null terminator
        length = self.read_uint32()
        if length == 0:
            return ""
        
        # Length includes null terminator
        string_bytes = self.read_bytes(length)
        # Remove null terminator and decode
        return string_bytes[:-1].decode('utf-8', errors='replace')
    
    def read_uint8(self):
        """Read an 8-bit unsigned integer"""
        return struct.unpack('<B', self.read_bytes(1))[0]
    
    def read_guid(self):
        """Read a GUID (16 bytes)"""
        guid_bytes = self.read_bytes(16)
        # Format as hex string: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        return '{:08X}{:08X}{:08X}{:08X}'.format(
            struct.unpack('<I', guid_bytes[0:4])[0],
            struct.unpack('<I', guid_bytes[4:8])[0],
            struct.unpack('<I', guid_bytes[8:12])[0],
            struct.unpack('<I', guid_bytes[12:16])[0]
        )
    
    def read_string_array(self):
        """Read an array of strings"""
        count = self.read_uint32()
        return [self.read_string() for _ in range(count)]
    
    def sha_to_decimal_string(self, sha_bytes):
        """Convert 20-byte SHA hash to decimal string (each byte as 3 digits)"""
        return ''.join(f"{b:03d}" for b in sha_bytes)
    
    def read_chunk_data_list(self):
        """Parse ChunkDataList (FChunkInfo.ReadChunkDataList)"""
        data_size = self.read_uint32()
        start_pos = self.offset
        data_version = self.read_uint8()  # EChunkDataListVersion
        element_count = self.read_uint32()
        
        print(f"\n=== Parsing ChunkDataList ===")
        print(f"Data size: {data_size}, version: {data_version}, element count: {element_count}")
        
        # Column-major layout: all of field X, then all of field Y
        guids = [self.read_guid() for _ in range(element_count)]
        hashes = [self.read_uint64() for _ in range(element_count)]
        sha_hashes = [self.read_bytes(20) for _ in range(element_count)]
        group_numbers = [self.read_uint8() for _ in range(element_count)]
        window_sizes = [self.read_uint32() for _ in range(element_count)]
        file_sizes = [self.read_uint64() for _ in range(element_count)]
        
        # Build lookup dicts for JSON format
        self.manifest['ChunkHashList'] = {guid: str(hash_val) for guid, hash_val in zip(guids, hashes)}
        self.manifest['ChunkShaList'] = {guid: sha.hex().upper() for guid, sha in zip(guids, sha_hashes)}
        self.manifest['DataGroupList'] = {guid: f"{group:03d}" for guid, group in zip(guids, group_numbers)}
        self.manifest['ChunkFilesizeList'] = {guid: str(size).zfill(24) for guid, size in zip(guids, file_sizes)}
        
        print(f"Created chunk lookup tables with {element_count} entries")
        
        # Seek to end of structure using data_size
        self.offset = start_pos + data_size
    
    def read_chunk_parts_array(self):
        """Read array of FChunkPart structs"""
        count = self.read_uint32()
        parts = []
        for _ in range(count):
            part_size = self.read_uint32()  # FChunkPart has its own size header
            guid = self.read_guid()
            offset = self.read_uint32()
            size = self.read_uint32()
            parts.append({
                'Guid': guid,
                'Offset': str(offset).zfill(12),
                'Size': str(size).zfill(12)
            })
        return parts
    
    def read_file_data_list(self):
        """Parse FileDataList (FFileManifest.ReadFileDataList)"""
        data_size = self.read_uint32()
        start_pos = self.offset
        data_version = self.read_uint8()  # EFileManifestListVersion
        element_count = self.read_uint32()
        
        print(f"\n=== Parsing FileDataList ===")
        print(f"Data size: {data_size}, version: {data_version}, element count: {element_count}")
        
        # Column-major: all filenames, then all symlinks, etc.
        filenames = [self.read_string() for _ in range(element_count)]
        symlinks = [self.read_string() for _ in range(element_count)]
        file_hashes = [self.read_bytes(20) for _ in range(element_count)]
        file_flags = [self.read_uint8() for _ in range(element_count)]
        install_tags = [self.read_string_array() for _ in range(element_count)]
        
        # Chunk parts for each file
        all_chunk_parts = []
        for i in range(element_count):
            chunk_parts = self.read_chunk_parts_array()
            all_chunk_parts.append(chunk_parts)
        
        # Build FileManifestList
        self.manifest['FileManifestList'] = []
        for i in range(element_count):
            self.manifest['FileManifestList'].append({
                'Filename': filenames[i],
                'FileHash': self.sha_to_decimal_string(file_hashes[i]),
                'FileChunkParts': all_chunk_parts[i]
            })
            if i < 3 or i >= element_count - 2:
                print(f"  File {i+1}/{element_count}: {filenames[i][:60]}")
            elif i == 3:
                print(f"  ... {element_count - 5} more files ...")
        
        print(f"Parsed {element_count} files")
        
        # Seek to end of structure using data_size
        self.offset = start_pos + data_size
    
    def read_custom_fields(self):
        """Parse CustomFields"""
        data_size = self.read_uint32()
        start_pos = self.offset
        data_version = self.read_uint8()
        element_count = self.read_uint32()
        
        print(f"\n=== Parsing CustomFields ===")
        print(f"Data size: {data_size}, version: {data_version}, element count: {element_count}")
        
        self.manifest['CustomFields'] = {}
        for _ in range(element_count):
            key = self.read_string()
            value = self.read_string()
            self.manifest['CustomFields'][key] = value
        
        print(f"Parsed {element_count} custom fields")
        
        # Seek to end of structure using data_size
        self.offset = start_pos + data_size
    
    def parse(self):
        """Parse the binary manifest file"""
        with open(self.filepath, 'rb') as f:
            self.data = f.read()
        
        # Parse header
        magic = struct.unpack('<I', self.data[0:4])[0]
        if magic != 0x44bec00c:
            raise ValueError(f"Invalid manifest magic: 0x{magic:08x}")
        
        header_size = struct.unpack('<I', self.data[4:8])[0]
        data_size_compressed = struct.unpack('<I', self.data[8:12])[0]
        data_size_uncompressed = struct.unpack('<I', self.data[12:16])[0]
        
        print(f"Magic: 0x{magic:08x}")
        print(f"Header size: {header_size}")
        print(f"Compressed size: {data_size_compressed}")
        print(f"Uncompressed size: {data_size_uncompressed}")
        
        # Start parsing from after header  
        # Epic format has metadata section before actual data
        self.offset = header_size
        
        # Parse metadata section (14 bytes: offsets 41-54)
        # Observed pattern: uint32, byte, uint32, uint64
        metadata_val1 = self.read_uint32()  # Appears to be 145 (0x91)
        metadata_flag = self.read_bytes(1)[0]  # 0x02
        metadata_val2 = self.read_uint32()  # 21 (0x15) - could be version
        metadata_zeros = self.read_uint32()  # 0x00
        metadata_final_byte = self.read_bytes(1)[0]  # Additional byte to reach offset 55
        
        print(f"Metadata: val1={metadata_val1}, flag={metadata_flag}, val2={metadata_val2}")
        
        # Try to extract version info from metadata
        # metadata_val2 (21 = 0x15) might encode version somehow
        # For now, construct from observed pattern
        if metadata_val2 == 21:
            self.manifest['ManifestFileVersion'] = f"{metadata_val2:012d}"  # "000000000021"
        else:
            self.manifest['ManifestFileVersion'] = f"{metadata_val2:012d}"
        
        self.manifest['bIsFileData'] = bool(metadata_flag & 0x01)
        self.manifest['AppID'] = '000000000000'  # Default
        
        # Try to parse the data structure
        try:
            # Read AppNameString (first actual string field)
            app_name = self.read_string()
            self.manifest['AppNameString'] = app_name
            print(f"App name: {app_name}")
            
            # Read BuildVersionString (second string field)
            build_version = self.read_string()
            self.manifest['BuildVersionString'] = build_version
            print(f"Build version: {build_version}")
            
            # Read LaunchExeString
            launch_exe = self.read_string()
            self.manifest['LaunchExeString'] = launch_exe
            
            # Read LaunchCommand
            launch_cmd = self.read_string()
            self.manifest['LaunchCommand'] = launch_cmd
            
            # Read PrereqIds (array)
            prereq_count = self.read_uint32()
            self.manifest['PrereqIds'] = []
            for _ in range(prereq_count):
                self.manifest['PrereqIds'].append(self.read_string())
            
            # Read PrereqName, PrereqPath, PrereqArgs
            self.manifest['PrereqName'] = self.read_string()
            self.manifest['PrereqPath'] = self.read_string()
            self.manifest['PrereqArgs'] = self.read_string()
            
            print(f"\nCurrent offset after string fields: {self.offset}")
            
            # Parse sequential structures using UE format
            self.read_chunk_data_list()  # Creates ChunkHashList, ChunkShaList, DataGroupList, ChunkFilesizeList
            self.read_file_data_list()   # Creates FileManifestList with all fields
            self.read_custom_fields()     # Creates CustomFields
            
            print(f"\nParsing complete at offset: {self.offset}")
            
        except Exception as e:
            print(f"Error during parsing: {e}")
            import traceback
            traceback.print_exc()
        
        return self.manifest
    
    def extract_strings(self):
        """Extract all readable strings from the manifest"""
        strings = []
        current = []
        
        for byte in self.data[41:]:  # Skip header
            if 32 <= byte <= 126:
                current.append(chr(byte))
            else:
                if len(current) >= 4:
                    strings.append(''.join(current))
                current = []
        
        return strings


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_binary_manifest.py <manifest_file> [output.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Parsing binary manifest: {input_file}\n")
    
    parser = BinaryManifestParser(input_file)
    
    try:
        manifest = parser.parse()
        
        # Also extract strings for comparison
        print("\n=== Extracting strings for comparison ===")
        strings = parser.extract_strings()
        
        # Find files from strings
        files = [s for s in strings if '/' in s and s.startswith('Content/')]
        print(f"Found {len(files)} file paths in strings")
        
        # Compare parsed vs string extraction
        parsed_count = len(manifest.get('FileManifestList', []))
        string_count = len(files)
        print(f"\n=== COMPARISON ===")
        print(f"Files from binary parsing: {parsed_count}")
        print(f"Files from string extraction: {string_count}")
        print(f"Match: {'✓ YES' if parsed_count == string_count else '✗ NO'}")
        
        if parsed_count != string_count:
            print(f"\nDifference: {abs(parsed_count - string_count)} files")
            if parsed_count < string_count:
                print("Note: String extraction found more files than binary parsing")
            else:
                print("Note: Binary parsing found more files than string extraction")
        
        # Extract CustomFields from strings
        manifest['CustomFields'] = {}
        for s in strings:
            if s.startswith('http'):
                if 'BaseUrl' not in manifest['CustomFields']:
                    manifest['CustomFields']['BaseUrl'] = s
                elif 'fab.com' in s and 'ThumbnailUrl' not in manifest['CustomFields']:
                    manifest['CustomFields']['ThumbnailUrl'] = s
        
        # Output results
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"\n✓ Saved parsed manifest to: {output_file}")
        else:
            print("\n=== PARSED MANIFEST ===")
            print(json.dumps(manifest, indent=2)[:2000])
            print("\n... (truncated)")
        
        # Print summary
        print(f"\n=== SUMMARY ===")
        print(f"App Name: {manifest.get('AppNameString', 'unknown')}")
        print(f"Build Version: {manifest.get('BuildVersionString', 'unknown')}")
        print(f"Total Files: {len(manifest.get('FileManifestList', []))}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
