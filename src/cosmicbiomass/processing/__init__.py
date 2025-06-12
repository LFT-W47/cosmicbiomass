"""Processing package initialization."""

from .footprint import FootprintProcessor, validate_footprint_coverage
from .statistics import StatisticsProcessor, BiomassStatistics

__all__ = [
    'FootprintProcessor', 
    'validate_footprint_coverage',
    'StatisticsProcessor', 
    'BiomassStatistics'
]
