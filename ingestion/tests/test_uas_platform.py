"""Tests for UAS platform integration.

This module tests the UAS marketplace integration including:
- UASSource with mocked client
- UASTransformer logic
- Integration with pipeline
- Graceful degradation when dependencies missing
"""

import pytest
from unittest.mock import Mock
from typing import List


# Check if uas-api-client is available
try:
    from game_asset_tracker_ingestion.platforms.uas import (
        UAS_AVAILABLE,
        UASAssetAdapter,
        UASSource,
        UASTransformer,
    )
    from game_asset_tracker_ingestion.sources.base import AssetData
    from game_asset_tracker_ingestion.core.validator import validate_manifest
    
    UAS_TESTS_ENABLED = UAS_AVAILABLE
except ImportError:
    UAS_TESTS_ENABLED = False


# Skip all tests if uas-api-client not installed
pytestmark = pytest.mark.skipif(
    not UAS_TESTS_ENABLED,
    reason="uas-api-client not installed"
)


# ============================================================================
# Mock Fixtures
# ============================================================================

class MockUnityAsset:
    """Mock Unity asset for testing."""
    
    def __init__(
        self,
        uid: str,
        title: str,
        description: str = "",
        publisher: str = "Unity Technologies",
        category: str = "3D",
        unity_version: str = "2021.3.0f1",
        price: float = 0.0,
        rating: float = 4.5,
        package_size: int = 1024 * 1024 * 100  # 100 MB
    ):
        self.uid = uid
        self.title = title
        self.description = description
        self.publisher = publisher
        self.publisher_id = f"{publisher.lower().replace(' ', '-')}-id"
        self.category = category
        self.unity_version = unity_version
        self.price = price
        self.rating = rating
        self.package_size = package_size
        self.dependencies = []
        self.download_url = f"https://cdn.unity.com/packages/{uid}.unitypackage.encrypted"
        self.download_s3_key = f"packages/{uid}"
        self.asset_count = 150
        self.created_at = "2024-01-01T00:00:00Z"
        self.updated_at = "2024-01-02T00:00:00Z"
        self.raw_data = {}
    
    def get_download_size_mb(self):
        """Calculate size in MB."""
        if self.package_size is None:
            return None
        return self.package_size / (1024 * 1024)


class MockUnityCollection:
    """Mock Unity collection for testing."""
    
    def __init__(self, assets: List[MockUnityAsset]):
        self.assets = assets
        self.total_count = len(assets)
    
    def __len__(self):
        return len(self.assets)


@pytest.fixture
def sample_unity_assets():
    """Sample Unity assets for testing."""
    return [
        MockUnityAsset(
            uid="330726",
            title="Fantasy Character Pack",
            description="A collection of fantasy characters",
            publisher="Epic Publisher",
            category="3D/Characters",
            unity_version="2021.3.0f1",
            price=49.99,
            rating=4.8
        ),
        MockUnityAsset(
            uid="330727",
            title="SciFi Environment Assets",
            description="Sci-fi environment assets",
            publisher="Unity Technologies",
            category="3D/Environments",
            unity_version="2020.3.0f1",
            price=0.0,  # Free asset
            rating=4.2
        ),
        MockUnityAsset(
            uid="330728",
            title="Audio Tools Pro",
            description="Professional audio tools",
            publisher="AudioCraft",
            category="Tools/Audio",
            unity_version="2022.1.0f1",
            price=29.99,
            rating=4.6
        ),
    ]


@pytest.fixture
def mock_unity_client(sample_unity_assets):
    """Mock UnityClient for testing."""
    client = Mock()
    collection = MockUnityCollection(sample_unity_assets)
    client.get_collection.return_value = collection
    return client


# ============================================================================
# TestUASSourceMocked
# ============================================================================

class TestUASSourceMocked:
    """Tests for UASSource with mocked client."""
    
    def test_list_assets_returns_all_from_collection(self, mock_unity_client):
        """Test that list_assets returns all assets from collection."""
        source = UASSource(mock_unity_client)
        assets = source.list_assets()
        
        assert len(assets) == 3
        assert assets[0].uid == "330726"
        assert assets[0].title == "Fantasy Character Pack"
        assert assets[0].source_type == "uas"
    
    def test_list_assets_returns_list_not_iterator(self, mock_unity_client):
        """Test that list_assets returns a list (not iterator)."""
        source = UASSource(mock_unity_client)
        assets = source.list_assets()
        
        assert isinstance(assets, list)
    
    def test_get_asset_returns_specific_asset(self, mock_unity_client):
        """Test retrieving a specific asset by UID."""
        source = UASSource(mock_unity_client)
        asset = source.get_asset("330727")
        
        assert asset.uid == "330727"
        assert asset.title == "SciFi Environment Assets"
    
    def test_get_asset_raises_for_unknown_uid(self, mock_unity_client):
        """Test that get_asset raises KeyError for unknown UID."""
        source = UASSource(mock_unity_client)
        
        with pytest.raises(KeyError, match="not found"):
            source.get_asset("nonexistent-uid")
    
    def test_get_asset_data_metadata_only(self, mock_unity_client):
        """Test get_asset_data in metadata-only mode."""
        source = UASSource(mock_unity_client)
        asset = source.get_asset("330726")
        asset_data = source.get_asset_data(asset, download=False)
        
        assert asset_data.asset == asset
        assert 'unity_asset' in asset_data.metadata
        assert asset_data.parsed_manifest is None
        assert len(asset_data.files) == 0
    
    def test_get_asset_data_download_raises_not_implemented(self, mock_unity_client):
        """Test that download mode raises NotImplementedError (Phase 3)."""
        source = UASSource(mock_unity_client)
        asset = source.get_asset("330726")
        
        with pytest.raises(NotImplementedError, match="Download mode not yet implemented"):
            source.get_asset_data(asset, download=True)
    
    def test_get_asset_data_validates_asset_type(self, mock_unity_client):
        """Test that get_asset_data validates asset is UASAssetAdapter."""
        source = UASSource(mock_unity_client)
        
        # Create a fake asset that's not UASAssetAdapter
        fake_asset = Mock()
        fake_asset.uid = "fake"
        
        with pytest.raises(ValueError, match="Expected UASAssetAdapter"):
            source.get_asset_data(fake_asset)
    
    def test_get_transformer_returns_uas_transformer(self, mock_unity_client):
        """Test that get_transformer returns UASTransformer instance."""
        source = UASSource(mock_unity_client)
        transformer = source.get_transformer()
        
        assert isinstance(transformer, UASTransformer)
    
    def test_collection_lazy_loaded(self, mock_unity_client):
        """Test that collection is lazy-loaded (not fetched until needed)."""
        source = UASSource(mock_unity_client)
        
        # Should not have called get_collection yet
        mock_unity_client.get_collection.assert_not_called()
        
        # Now fetch assets
        source.list_assets()
        
        # Should have called get_collection exactly once
        mock_unity_client.get_collection.assert_called_once()
        
        # Second call should reuse cached collection
        source.list_assets()
        mock_unity_client.get_collection.assert_called_once()


# ============================================================================
# TestUASTransformer
# ============================================================================

class TestUASTransformer:
    """Tests for UASTransformer."""
    
    def test_transform_creates_valid_manifest(self, sample_unity_assets):
        """Test basic transformation to manifest."""
        transformer = UASTransformer()
        unity_asset = sample_unity_assets[0]
        source_asset = UASAssetAdapter(unity_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(source_asset, asset_data)
        
        # Validate against schema
        validate_manifest(manifest)
        
        # Check pack-level fields
        assert manifest['pack_name'] == "Fantasy Character Pack"
        assert manifest['source'] == "UAS - Unity Asset Store"
        assert manifest['root_path'] == "N/A"
        assert isinstance(manifest['pack_id'], str)
        assert len(manifest['assets']) == 1
    
    def test_transform_uses_custom_pack_name(self, sample_unity_assets):
        """Test that custom pack_name overrides asset title."""
        transformer = UASTransformer()
        unity_asset = sample_unity_assets[0]
        source_asset = UASAssetAdapter(unity_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(
            source_asset,
            asset_data,
            pack_name="Custom Pack Name"
        )
        
        assert manifest['pack_name'] == "Custom Pack Name"
    
    def test_transform_accepts_global_tags(self, sample_unity_assets):
        """Test that global_tags are included in manifest."""
        transformer = UASTransformer()
        unity_asset = sample_unity_assets[0]
        source_asset = UASAssetAdapter(unity_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(
            source_asset,
            asset_data,
            global_tags=['unity', 'marketplace', '3d']
        )
        
        assert manifest['global_tags'] == ['unity', 'marketplace', '3d']
    
    def test_transform_accepts_license_link(self, sample_unity_assets):
        """Test that license_link is included in manifest."""
        transformer = UASTransformer()
        unity_asset = sample_unity_assets[0]
        source_asset = UASAssetAdapter(unity_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(
            source_asset,
            asset_data,
            license_link="https://unity.com/legal/as_terms"
        )
        
        assert manifest['license_link'] == "https://unity.com/legal/as_terms"
    
    def test_placeholder_asset_has_correct_metadata(self, sample_unity_assets):
        """Test that placeholder asset includes Unity-specific metadata."""
        transformer = UASTransformer()
        unity_asset = sample_unity_assets[0]
        source_asset = UASAssetAdapter(unity_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(source_asset, asset_data)
        asset = manifest['assets'][0]
        
        # Check asset structure
        assert asset['relative_path'] == "Fantasy Character Pack"
        assert asset['file_type'] == "marketplace"
        assert asset['size_bytes'] == unity_asset.package_size
        assert asset['local_tags'] == []
        
        # Check metadata
        metadata = asset['metadata']
        assert metadata['publisher'] == "Epic Publisher"
        assert metadata['category'] == "3D/Characters"
        assert metadata['unity_version'] == "2021.3.0f1"
        assert metadata['price'] == "49.99"
        assert metadata['rating'] == "4.8"
        assert 'package_size_mb' in metadata
        assert metadata['download_available'] == 'true'
    
    def test_placeholder_asset_handles_free_assets(self, sample_unity_assets):
        """Test that free assets (price=0) are handled correctly."""
        transformer = UASTransformer()
        unity_asset = sample_unity_assets[1]  # Free asset
        source_asset = UASAssetAdapter(unity_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(source_asset, asset_data)
        asset = manifest['assets'][0]
        
        assert asset['metadata']['price'] == "0.0"
    
    def test_placeholder_asset_handles_missing_optional_fields(self):
        """Test that transformer handles assets with missing optional fields."""
        transformer = UASTransformer()
        
        # Create minimal asset with no optional fields
        minimal_asset = MockUnityAsset(
            uid="minimal",
            title="Minimal Asset",
            description=""
        )
        minimal_asset.publisher = None
        minimal_asset.category = None
        minimal_asset.unity_version = None
        minimal_asset.price = None
        minimal_asset.rating = None
        minimal_asset.package_size = None
        minimal_asset.download_url = None
        
        source_asset = UASAssetAdapter(minimal_asset)
        asset_data = AssetData(
            asset=source_asset,
            metadata={'unity_asset': minimal_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(source_asset, asset_data)
        
        # Should still create valid manifest
        validate_manifest(manifest)
        
        asset = manifest['assets'][0]
        assert asset['size_bytes'] == 0
        assert asset['metadata']['download_available'] == 'false'
    
    def test_transform_raises_for_missing_unity_asset(self):
        """Test that transform raises ValueError if unity_asset missing."""
        transformer = UASTransformer()
        
        fake_asset = Mock()
        fake_asset.uid = "fake"
        fake_asset.title = "Fake"
        
        asset_data = AssetData(
            asset=fake_asset,
            metadata={},  # Missing 'unity_asset'
            files=[],
            parsed_manifest=None,
        )
        
        with pytest.raises(ValueError, match="missing 'unity_asset'"):
            transformer.transform(fake_asset, asset_data)


# ============================================================================
# TestUASAssetAdapter
# ============================================================================

class TestUASAssetAdapter:
    """Tests for UASAssetAdapter."""
    
    def test_adapter_implements_source_asset_protocol(self, sample_unity_assets):
        """Test that adapter implements SourceAsset protocol."""
        unity_asset = sample_unity_assets[0]
        adapter = UASAssetAdapter(unity_asset)
        
        # Should have required properties
        assert hasattr(adapter, 'uid')
        assert hasattr(adapter, 'title')
        assert hasattr(adapter, 'description')
        assert hasattr(adapter, 'source_type')
    
    def test_adapter_exposes_unity_asset_properties(self, sample_unity_assets):
        """Test that adapter correctly exposes Unity asset properties."""
        unity_asset = sample_unity_assets[0]
        adapter = UASAssetAdapter(unity_asset)
        
        assert adapter.uid == "330726"
        assert adapter.title == "Fantasy Character Pack"
        assert adapter.description == "A collection of fantasy characters"
        assert adapter.source_type == "uas"
    
    def test_adapter_provides_raw_asset_access(self, sample_unity_assets):
        """Test that adapter provides access to raw Unity asset."""
        unity_asset = sample_unity_assets[0]
        adapter = UASAssetAdapter(unity_asset)
        
        assert adapter.raw_asset is unity_asset
        assert adapter.raw_asset.publisher == "Epic Publisher"
    
    def test_adapter_handles_empty_description(self):
        """Test that adapter handles None description."""
        unity_asset = MockUnityAsset(
            uid="test",
            title="Test Asset",
            description=None
        )
        adapter = UASAssetAdapter(unity_asset)
        
        assert adapter.description == ""
