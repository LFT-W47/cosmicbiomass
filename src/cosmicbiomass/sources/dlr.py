"""DLR Global Aboveground Biomass Density data source implementation."""

import logging
from typing import Any

import cubo
import xarray as xr

from ..config import BiomassConfig
from .base import BiomassDataSource, DatasetInfo

logger = logging.getLogger(__name__)


class DLRBiomassSource(BiomassDataSource):
    """DLR Global Aboveground Biomass Density data source using STAC."""

    def __init__(self, config: BiomassConfig):
        super().__init__(config)
        # DLR STAC configuration
        self.stac_url = "https://geoservice.dlr.de/eoc/ogc/stac/v1"
        self.collection = "FOREST_STRUCTURE_DE_AGBD_P1Y"
        self.resolution = 10

    @property
    def source_name(self) -> str:
        return "DLR"

    def get_available_datasets(self) -> dict[str, DatasetInfo]:
        """Get information about available DLR datasets."""
        return {
            "agbd_2017": DatasetInfo(
                id="agbd_2017",
                name="AGBD 2017",
                description="DLR Global Aboveground Biomass Density 2017",
                spatial_resolution=10.0,
                temporal_coverage="2017-01-01/2017-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            ),
            "agbd_2018": DatasetInfo(
                id="agbd_2018",
                name="AGBD 2018",
                description="DLR Global Aboveground Biomass Density 2018",
                spatial_resolution=10.0,
                temporal_coverage="2018-01-01/2018-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            ),
            "agbd_2019": DatasetInfo(
                id="agbd_2019",
                name="AGBD 2019",
                description="DLR Global Aboveground Biomass Density 2019",
                spatial_resolution=10.0,
                temporal_coverage="2019-01-01/2019-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            ),
            "agbd_2020": DatasetInfo(
                id="agbd_2020",
                name="AGBD 2020",
                description="DLR Global Aboveground Biomass Density 2020",
                spatial_resolution=10.0,
                temporal_coverage="2020-01-01/2020-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            ),
            "agbd_2021": DatasetInfo(
                id="agbd_2021",
                name="AGBD 2021",
                description="DLR Global Aboveground Biomass Density 2021",
                spatial_resolution=10.0,
                temporal_coverage="2021-01-01/2021-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            ),
            "agbd_2022": DatasetInfo(
                id="agbd_2022",
                name="AGBD 2022",
                description="DLR Global Aboveground Biomass Density 2022",
                spatial_resolution=10.0,
                temporal_coverage="2022-01-01/2022-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            ),
            "agbd_2023": DatasetInfo(
                id="agbd_2023",
                name="AGBD 2023",
                description="DLR Global Aboveground Biomass Density 2023",
                spatial_resolution=10.0,
                temporal_coverage="2023-01-01/2023-12-31",
                units="Mg/ha",
                uncertainty_available=True,
                crs="EPSG:32632"
            )
        }

    def load_data(self, dataset_id: str, bbox: tuple[float, float, float, float] | None = None) -> xr.Dataset:
        """Load DLR biomass data using STAC catalog."""
        datasets = self.get_available_datasets()
        if dataset_id not in datasets:
            raise ValueError(f"Dataset {dataset_id} not available. Available: {list(datasets.keys())}")

        dataset_info = datasets[dataset_id]
        year = dataset_id.split('_')[1]

        logger.info(f"Loading DLR dataset {dataset_id} via STAC")

        # Calculate edge size from bbox if provided
        if bbox is not None:
            # bbox is (minx, miny, maxx, maxy)
            # Convert to approximate edge size in meters
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

            # Transform bbox corners to meters for size calculation
            x1, y1 = transformer.transform(bbox[0], bbox[1])
            x2, y2 = transformer.transform(bbox[2], bbox[3])

            edge_size = max(abs(x2 - x1), abs(y2 - y1))
            center_lon = (bbox[0] + bbox[2]) / 2
            center_lat = (bbox[1] + bbox[3]) / 2
        else:
            # Default values if no bbox
            edge_size = 2000  # 2km default
            center_lon = 11.226  # Default to Hohes Holz
            center_lat = 52.09

        try:
            # Use cubo to extract data from STAC
            cube_params = {
                "lat": center_lat,
                "lon": center_lon,
                "stac": self.stac_url,
                "collection": self.collection,
                "gee": False,
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-12-31",
                "edge_size": int(edge_size),
                "units": "m",
                "resolution": self.resolution,
            }

            logger.debug(f"Cubo parameters: {cube_params}")
            ds = cubo.create(**cube_params)

            logger.info(f"Successfully loaded dataset with shape: {ds.sizes}")

            # Add dataset metadata
            ds.attrs.update({
                'source': 'DLR',
                'dataset_id': dataset_id,
                'units': dataset_info.units,
                'spatial_resolution': dataset_info.spatial_resolution,
                'temporal_coverage': dataset_info.temporal_coverage
            })

            return ds

        except Exception as e:
            logger.error(f"Failed to load via STAC: {e}")
            raise

    def get_metadata(self, dataset_id: str) -> dict[str, Any]:
        """Get metadata for a DLR dataset."""
        datasets = self.get_available_datasets()
        if dataset_id not in datasets:
            raise ValueError(f"Dataset {dataset_id} not available")

        dataset_info = datasets[dataset_id]
        return {
            'source': self.source_name,
            'dataset_info': dataset_info.dict(),
            'data_format': 'GeoTIFF COG',
            'coordinate_system': dataset_info.crs,
            'processing_level': 'L3',
            'quality_flags': 'Available in uncertainty band'
        }
