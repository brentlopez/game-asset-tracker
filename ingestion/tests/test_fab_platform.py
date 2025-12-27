"""Tests for Fab platform integration.

This module tests the Fab marketplace integration including:
- FabSource with mocked client
- FabTransformer logic
- Integration with pipeline
- Graceful degradation when dependencies missing
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List


# Check if fab-api-client is available
try:
    from game_asset_tracker_ingestion.platforms.fab import (
        FAB_AVAILABLE,
        FabAssetAdapter,
        FabSource,
        FabTransformer,
    )
    from game_asset_tracker_ingestion.sources.base import AssetData
    from game_asset_tracker_ingestion.core.validator import validate_manifest
    
    FAB_TESTS_ENABLED = FAB_AVAILABLE
except ImportError:
    FAB_TESTS_ENABLED = False


# Skip all tests if fab-api-client not installed
pytestmark = pytest.mark.skipif(
    not FAB_TESTS_ENABLED,
    reason="fab-api-client not installed"
)


# ============================================================================
# Mock Fixtures
# ============================================================================

class MockFabAsset:
    """Mock Fab asset for testing."""
    
    def __init__(
        self,
        uid: str,
        title: str,
        description: str = "",
        status: str = "ACTIVE",
        entitlement: bool = True
    ):
        self.uid = uid
        self.title = title
        self.description = description
        self.status = status
        self.entitlement = entitlement
        self.created_at = "2024-01-01T00:00:00Z"
        self.updated_at = "2024-01-02T00:00:00Z"
        
        # Mock listing
        self.listing = Mock()
        self.listing.uid = f"{uid}-listing"
        self.listing.seller = Mock()
        self.listing.seller.name = "Epic Games"
        self.listing.license_url = "https://example.com/license"
        self.listing.current_price = 0
        
        # Mock licenses
        self.granted_licenses = ["license1", "license2"]


class MockLibrary:
    """Mock Fab library for testing."""
    
    def __init__(self, assets: List[MockFabAsset]):
        self.assets = assets


@pytest.fixture
def sample_fab_assets():
    """Sample Fab assets for testing."""
    return [
        MockFabAsset(
            uid="asset-1",
            title="Fantasy 3D Models",
            description="A collection of fantasy characters",
            status="ACTIVE",
            entitlement=True
        ),
        MockFabAsset(
            uid="asset-2",
            title="SciFi Materials",
            description="PBR materials for sci-fi environments",
            status="ACTIVE",
            entitlement=True
        ),
        MockFabAsset(
            uid="asset-3",
            title="Sound Effects Pack",
            description="High-quality sound effects",
            status="EXPIRED",
            entitlement=False
        ),
    ]


@pytest.fixture
def mock_fab_client(sample_fab_assets):
    """Mock FabClient for testing."""
    client = Mock()
    library = MockLibrary(sample_fab_assets)
    client.get_library.return_value = library
    return client


# ============================================================================
# TestFabSourceMocked
# ============================================================================

class TestFabSourceMocked:
    """Tests for FabSource with mocked client."""
    
    def test_list_assets_returns_all_library_assets(self, mock_fab_client):
        """Test that list_assets returns all assets from library."""
        source = FabSource(mock_fab_client)
        assets = source.list_assets()
        
        assert len(assets) == 3
        assert assets[0].uid == "asset-1"
        assert assets[0].title == "Fantasy 3D Models"
        assert assets[0].source_type == "fab"
    
    def test_list_assets_returns_list_not_iterator(self, mock_fab_client):
        """Test that list_assets returns a list (not iterator)."""
        source = FabSource(mock_fab_client)
        assets = source.list_assets()
        
        assert isinstance(assets, list)
    
    def test_get_asset_returns_specific_asset(self, mock_fab_client):
        """Test retrieving a specific asset by UID."""
        source = FabSource(mock_fab_client)
        asset = source.get_asset("asset-2")
        
        assert asset.uid == "asset-2"
        assert asset.title == "SciFi Materials"
    
    def test_get_asset_raises_for_unknown_uid(self, mock_fab_client):
        """Test that get_asset raises KeyError for unknown UID."""
        source = FabSource(mock_fab_client)
        
        with pytest.raises(KeyError, match="not found"):
            source.get_asset("nonexistent-uid")
    
    def test_get_asset_data_metadata_only(self, mock_fab_client):
        """Test get_asset_data in metadata-only mode."""
        source = FabSource(mock_fab_client)
        asset = source.get_asset("asset-1")
        asset_data = source.get_asset_data(asset, download=False)
        
        assert asset_data.asset == asset
        assert 'fab_asset' in asset_data.metadata
        assert asset_data.files == []
        assert asset_data.parsed_manifest is None
    
    def test_get_asset_data_download_not_implemented(self, mock_fab_client):
        """Test that download=True raises NotImplementedError in Phase 2."""
        source = FabSource(mock_fab_client)
        asset = source.get_asset("asset-1")
        
        with pytest.raises(NotImplementedError, match="Phase 3"):
            source.get_asset_data(asset, download=True)
    
    def test_library_lazy_loaded(self, mock_fab_client):
        """Test that library is only fetched once."""
        source = FabSource(mock_fab_client)
        
        # First call
        source.list_assets()
        assert mock_fab_client.get_library.call_count == 1
        
        # Second call should use cached library
        source.list_assets()
        assert mock_fab_client.get_library.call_count == 1
    
    def test_get_transformer_returns_transformer(self, mock_fab_client):
        """Test that get_transformer returns FabTransformer."""
        source = FabSource(mock_fab_client)
        transformer = source.get_transformer()
        
        assert isinstance(transformer, FabTransformer)
    
    def test_asset_adapter_has_required_properties(self, sample_fab_assets):
        """Test that FabAssetAdapter implements SourceAsset protocol."""
        fab_asset = sample_fab_assets[0]
        adapter = FabAssetAdapter(fab_asset)
        
        assert adapter.uid == "asset-1"
        assert adapter.title == "Fantasy 3D Models"
        assert adapter.description == "A collection of fantasy characters"
        assert adapter.source_type == "fab"
        assert adapter.raw_asset == fab_asset


# ============================================================================
# TestFabTransformer
# ============================================================================

class TestFabTransformer:
    """Tests for FabTransformer."""
    
    def test_transform_creates_valid_manifest(self, sample_fab_assets):
        """Test basic transformation to manifest."""
        transformer = FabTransformer()
        fab_asset = sample_fab_assets[0]
        source_asset = FabAssetAdapter(fab_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'fab_asset': fab_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(source_asset, asset_data)
        
        # Validate against schema
        validate_manifest(manifest)
        
        # Check pack-level fields
        assert manifest['pack_name'] == "Fantasy 3D Models"
        assert manifest['source'] == "Fab - Epic Games"
        assert manifest['root_path'] == "N/A"  # Marketplace assets use N/A
        assert manifest['license_link'] == "https://example.com/license"
    
    def test_transform_uses_custom_pack_name(self, sample_fab_assets):
        """Test that pack_name override works."""
        transformer = FabTransformer()
        fab_asset = sample_fab_assets[0]
        source_asset = FabAssetAdapter(fab_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'fab_asset': fab_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(
            source_asset,
            asset_data,
            pack_name="Custom Pack Name"
        )
        
        assert manifest['pack_name'] == "Custom Pack Name"
    
    def test_transform_creates_placeholder_asset(self, sample_fab_assets):
        """Test that placeholder asset is created in Phase 2."""
        transformer = FabTransformer()
        fab_asset = sample_fab_assets[0]
        source_asset = FabAssetAdapter(fab_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'fab_asset': fab_asset},
            files=[],
            parsed_manifest=None,
        )
        
        manifest = transformer.transform(source_asset, asset_data)
        
        # Should have exactly one placeholder asset
        assert len(manifest['assets']) == 1
        
        asset = manifest['assets'][0]
        assert asset['file_type'] == 'marketplace'
        assert asset['size_bytes'] == 0
        assert asset['relative_path'] == "Fantasy 3D Models"
        assert asset['local_tags'] == []
        
        # Check metadata contains Fab-specific fields
        assert 'status' in asset['metadata']
        assert asset['metadata']['status'] == 'ACTIVE'
        assert 'entitled' in asset['metadata']
        assert asset['metadata']['entitled'] == 'true'
        assert 'listing_uid' in asset['metadata']
        assert 'seller_name' in asset['metadata']
    
    def test_transform_handles_missing_metadata(self):
        """Test transformer handles assets with minimal metadata."""
        # Minimal mock asset (no listing, no optional fields)
        minimal_asset = Mock(spec=['uid', 'title', 'description'])
        minimal_asset.uid = "minimal"
        minimal_asset.title = "Minimal Asset"
        minimal_asset.description = ""
        
        transformer = FabTransformer()
        source_asset = FabAssetAdapter(minimal_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={'fab_asset': minimal_asset},
            files=[],
            parsed_manifest=None,
        )
        
        # Should not raise even with missing optional fields
        manifest = transformer.transform(source_asset, asset_data)
        
        assert manifest['pack_name'] == "Minimal Asset"
        assert manifest['license_link'] == ""  # No listing, so should be empty
    
    def test_transform_raises_without_fab_asset(self):
        """Test that transform raises if fab_asset missing from metadata."""
        transformer = FabTransformer()
        minimal_asset = Mock()
        minimal_asset.title = "Test"
        source_asset = FabAssetAdapter(minimal_asset)
        
        asset_data = AssetData(
            asset=source_asset,
            metadata={},  # Missing fab_asset
            files=[],
            parsed_manifest=None,
        )
        
        with pytest.raises(ValueError, match="missing 'fab_asset'"):
            transformer.transform(source_asset, asset_data)


# ============================================================================
# TestFabIntegration
# ============================================================================

class TestFabIntegration:
    """Integration tests with IngestionPipeline."""
    
    def test_pipeline_creation_via_registry(self, mock_fab_client):
        """Test creating Fab pipeline via SourceRegistry."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        # Check Fab is registered
        assert 'fab' in SourceRegistry.list_sources()
        
        # Create pipeline
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        assert pipeline is not None
        assert pipeline.download_strategy == 'metadata_only'
    
    def test_generate_manifests_yields_all_assets(self, mock_fab_client):
        """Test that generate_manifests yields one manifest per asset."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        manifests = list(pipeline.generate_manifests())
        
        assert len(manifests) == 3
        assert manifests[0]['pack_name'] == "Fantasy 3D Models"
        assert manifests[1]['pack_name'] == "SciFi Materials"
        assert manifests[2]['pack_name'] == "Sound Effects Pack"
    
    def test_generate_manifests_validates_schema(self, mock_fab_client):
        """Test that all generated manifests are valid."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        for manifest in pipeline.generate_manifests():
            # Should not raise ValidationError
            validate_manifest(manifest)
    
    def test_generate_manifest_for_asset_single(self, mock_fab_client):
        """Test generating manifest for single asset."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        # Get specific asset
        asset = pipeline.source.get_asset("asset-2")
        manifest = pipeline.generate_manifest_for_asset(asset)
        
        assert manifest['pack_name'] == "SciFi Materials"
        validate_manifest(manifest)


# ============================================================================
# TestFabGracefulDegradation
# ============================================================================

class TestFabGracefulDegradation:
    """Tests for graceful handling when fab-api-client not installed."""
    
    def test_module_can_import_without_fab_api_client(self):
        """Test that fab platform module can be imported."""
        # This test runs even without fab-api-client
        try:
            from game_asset_tracker_ingestion.platforms import fab
            # If fab-api-client not available, FAB_AVAILABLE should be False
            if not FAB_TESTS_ENABLED:
                assert fab.FAB_AVAILABLE is False
        except ImportError:
            pytest.fail("Platform module should load even without dependencies")
    
    def test_registry_discovery_handles_missing_dependencies(self):
        """Test that registry discovery doesn't break with missing deps."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        # Should not raise even if some platforms missing
        sources = SourceRegistry.list_sources()
        assert isinstance(sources, list)
        
        # If fab-api-client installed, 'fab' should be in sources
        if FAB_TESTS_ENABLED:
            assert 'fab' in sources
