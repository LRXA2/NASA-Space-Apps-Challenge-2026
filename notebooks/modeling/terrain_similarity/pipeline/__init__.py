"""Compare one prepared Moon site with one Earth site using the saved CNN."""

from .artifacts import ArtifactConfig, TerrainModel
from .main import SiteComparison, compare_sites, run_inference

__all__ = [
    "ArtifactConfig",
    "SiteComparison",
    "TerrainModel",
    "compare_sites",
    "run_inference",
]
