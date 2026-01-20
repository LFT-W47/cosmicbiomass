#!/usr/bin/env python3
"""
Flowchart visualization of the CosmicBiomass workflow
This script creates a comprehensive flowchart showing how the cosmicbiomass package works.
"""

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch


def create_cosmicbiomass_flowchart():
    """Create a comprehensive flowchart of the CosmicBiomass workflow."""

    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(16, 20))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 25)
    ax.axis('off')

    # Define colors for different components
    colors = {
        'input': '#E3F2FD',        # Light blue
        'config': '#F3E5F5',       # Light purple
        'registry': '#E8F5E8',     # Light green
        'data': '#FFF3E0',         # Light orange
        'processing': '#F0F4C3',   # Light yellow-green
        'analysis': '#FFE0B2',     # Light orange
        'output': '#C8E6C9',       # Light green
        'error': '#FFCDD2',        # Light red
        'decision': '#FFF9C4'      # Light yellow
    }

    # Title
    ax.text(5, 24, 'CosmicBiomass Workflow',
            fontsize=20, fontweight='bold', ha='center')
    ax.text(5, 23.5, 'Satellite Biomass Extraction with Footprint Weighting',
            fontsize=14, ha='center', style='italic')

    # Helper function to create boxes
    def create_box(x, y, width, height, text, color, text_size=9):
        box = FancyBboxPatch((x-width/2, y-height/2), width, height,
                           boxstyle="round,pad=0.05",
                           facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(box)
        ax.text(x, y, text, ha='center', va='center', fontsize=text_size,
                wrap=True, fontweight='bold' if 'START' in text or 'END' in text else 'normal')

    # Helper function to create arrows
    def create_arrow(x1, y1, x2, y2, label='', offset=0.1):
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        dx_norm = dx / length
        dy_norm = dy / length

        # Adjust start and end points to not overlap with boxes
        start_x = x1 + dx_norm * offset
        start_y = y1 + dy_norm * offset
        end_x = x2 - dx_norm * offset
        end_y = y2 - dy_norm * offset

        ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                   arrowprops={'arrowstyle': '->', 'lw': 1.5, 'color': 'black'})

        # Add label if provided
        if label:
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            ax.text(mid_x, mid_y, label, ha='center', va='center',
                   fontsize=8, bbox={'boxstyle': "round,pad=0.2",
                   'facecolor': 'white', 'edgecolor': 'none'})

    # Helper function to create decision diamond
    def create_diamond(x, y, width, height, text, color):
        diamond = mpatches.RegularPolygon((x, y), 4, radius=width/2,
                                        orientation=np.pi/4,
                                        facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(diamond)
        ax.text(x, y, text, ha='center', va='center', fontsize=8, fontweight='bold')

    # 1. Input Parameters
    create_box(2.5, 22, 2.5, 1, 'START\nUser Input Parameters\n\n• lat, lon (coordinates)\n• radius (meters)\n• dataset (year)\n• footprint_shape\n• source ("dlr")', colors['input'])

    # 2. Configuration Setup
    create_box(7.5, 22, 2.5, 1, 'Configuration Setup\n\n• BiomassConfig\n• FootprintConfig\n• Processing parameters', colors['config'])

    # 3. Source Registry
    create_box(2.5, 20, 2.5, 1, 'Source Registry\n\n• get_source()\n• Resolve data source\n• Create DLRBiomassSource\n  instance', colors['registry'])

    # 4. Bounding Box Calculation
    create_box(7.5, 20, 2.5, 1, 'Bounding Box\nCalculation\n\n• Convert radius to degrees\n• Add buffer for data loading\n• bbox = (lon±, lat±)', colors['processing'])

    # 5. Data Loading
    create_box(5, 18, 3, 1, 'Data Loading\n\n• Connect to DLR STAC API\n• Load AGBD data using cubo\n• Apply spatial bbox filter\n• Return xarray.Dataset', colors['data'])

    # 6. Error handling for data loading
    create_diamond(8.5, 18, 1.5, 1, 'Data\nLoaded\nOK?', colors['decision'])
    create_box(8.5, 16.5, 2, 0.8, 'ERROR\nData loading failed\nRaise exception', colors['error'])

    # 7. Processor Initialization
    create_box(2.5, 16, 2.5, 1, 'Initialize Processors\n\n• FootprintProcessor\n• StatisticsProcessor\n• Configure parameters', colors['processing'])

    # 8. Footprint Weight Computation
    create_box(5, 14, 3.5, 1.5, 'Footprint Weight Computation\n\n• Transform coordinates to data CRS\n• Calculate distance grid from center\n• Apply footprint function:\n  - CRNS (Schrön et al. 2017)\n  - Circular (binary)\n  - Gaussian (exponential)', colors['processing'])

    # 9. Footprint validation
    create_diamond(1.5, 14, 1.5, 1, 'Footprint\nCoverage\nOK?', colors['decision'])
    create_box(1.5, 12.5, 2, 0.8, 'WARNING\nLow coverage\nResults unreliable', colors['error'])

    # 10. Variable Detection
    create_box(8.5, 14, 2.5, 1, 'Variable Detection\n\n• Primary: "agbd_cog"\n• Uncertainty bands:\n  - agbd_cog_uncertainty\n  - uncertainty, std, stderr', colors['processing'])

    # 11. Statistical Processing
    create_box(5, 11.5, 4, 1.5, 'Weighted Statistical Analysis\n\n• Mask invalid data (NaN, negative)\n• Apply footprint weights\n• Outlier detection (IQR/Z-score)\n• Compute weighted statistics:\n  - Mean, std, median, min, max\n  - Uncertainty from separate band or data spread', colors['analysis'])

    # 12. Coverage validation
    create_diamond(1.5, 11.5, 1.5, 1, 'Valid\nData\nFound?', colors['decision'])
    create_box(1.5, 10, 2, 0.8, 'WARNING\nNo valid data points\nReturn NaN statistics', colors['error'])

    # 13. Metadata Collection
    create_box(8.5, 11.5, 2.5, 1, 'Metadata Collection\n\n• Dataset information\n• Spatial resolution\n• Temporal coverage\n• Units (Mg/ha)', colors['data'])

    # 14. Result Assembly
    create_box(5, 9, 4, 1.5, 'Result Assembly\n\n• biomass_statistics (mean, std, etc.)\n• location (lat, lon, radius)\n• footprint (shape, coverage, weights)\n• data_info (source, dataset, units)\n• processing (outlier_method, uncertainty)\n• summary (formatted results)', colors['output'])

    # 15. Uncertainty Handling
    create_diamond(8.5, 9, 1.5, 1, 'Uncertainty\nBand\nAvailable?', colors['decision'])
    create_box(8.5, 7.5, 2, 0.8, 'Use uncertainty band\nsource: "uncertainty_band"', colors['output'])
    create_box(8.5, 6, 2, 0.8, 'Use data spread (std)\nsource: "data_spread"', colors['output'])

    # 16. Final Output
    create_box(5, 6.5, 3, 1, 'END\nReturn Results Dictionary\n\nMean AGBD ± Uncertainty\n(Mg/ha)', colors['output'])

    # 17. Advanced Features (side panel)
    create_box(1, 8, 2, 2, 'Advanced Features\n\n• Multi-year analysis\n• Custom footprint shapes\n• CRNS weighting\n• Outlier detection\n• Uncertainty quantification\n• Modular architecture', colors['config'])

    # 18. Data Sources (side panel)
    create_box(1, 5, 2, 1.5, 'Data Sources\n\n• DLR STAC API\n• 2017-2023 coverage\n• 10m resolution\n• UTM projection\n• Uncertainty included', colors['data'])

    # Create arrows for main flow
    create_arrow(2.5, 21.5, 2.5, 20.5)  # Input to Registry
    create_arrow(3.5, 22, 6.5, 22)      # Input to Config
    create_arrow(7.5, 21.5, 7.5, 20.5)  # Config to BBox
    create_arrow(2.5, 19.5, 4, 18.5)    # Registry to Data Loading
    create_arrow(7.5, 19.5, 6, 18.5)    # BBox to Data Loading
    create_arrow(5, 17.5, 5, 16.5)      # Data Loading down
    create_arrow(6.5, 18, 7.5, 18)      # Data Loading to Decision
    create_arrow(8.5, 17.5, 8.5, 17)    # Decision to Error (No)
    create_arrow(7, 18, 3.5, 16.5)      # Data Loading to Processors (Yes)
    create_arrow(2.5, 15.5, 4, 14.7)    # Processors to Footprint
    create_arrow(1.5, 13.5, 1.5, 13)    # Footprint Decision to Warning
    create_arrow(6.5, 14, 7.5, 14)      # Footprint to Variables
    create_arrow(5, 13.5, 5, 12.5)      # Footprint to Statistics
    create_arrow(1.5, 11, 1.5, 10.5)    # Statistics Decision to Warning
    create_arrow(8.5, 13.5, 8.5, 12)    # Variables to Metadata
    create_arrow(5, 10.5, 5, 10)        # Statistics to Results
    create_arrow(8.5, 11, 6.5, 9.5)     # Metadata to Results
    create_arrow(8.5, 8.5, 8.5, 8)      # Uncertainty Decision to Band (Yes)
    create_arrow(8.5, 8.5, 8.5, 6.5)    # Uncertainty Decision to Spread (No)
    create_arrow(5, 8.5, 5, 7.5)        # Results to Final

    # Add side connections
    create_arrow(1, 7, 3.5, 8.5, label='supports')
    create_arrow(1, 6, 3.5, 7, label='provides')

    # Add legend
    legend_elements = [
        mpatches.Patch(color=colors['input'], label='User Input'),
        mpatches.Patch(color=colors['config'], label='Configuration'),
        mpatches.Patch(color=colors['registry'], label='Registry/Factory'),
        mpatches.Patch(color=colors['data'], label='Data Operations'),
        mpatches.Patch(color=colors['processing'], label='Processing'),
        mpatches.Patch(color=colors['analysis'], label='Analysis'),
        mpatches.Patch(color=colors['output'], label='Output'),
        mpatches.Patch(color=colors['decision'], label='Decision Point'),
        mpatches.Patch(color=colors['error'], label='Error/Warning')
    ]

    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))

    # Add architecture notes
    ax.text(5, 3.5, 'CosmicBiomass Architecture Notes', fontsize=12, fontweight='bold', ha='center')
    architecture_text = """
• Modular design with pluggable data sources and processing components
• CRNS weighting implements Schrön et al. (2017) cosmic ray neutron sensing formula
• Supports multiple footprint shapes: circular, Gaussian, and CRNS
• Built-in uncertainty quantification and outlier detection
• Modern Python 3.10+ with type hints and comprehensive testing
• Uses xarray for N-dimensional data handling and dask for scalability
• STAC-compliant data access for interoperability
"""
    ax.text(5, 2.5, architecture_text, fontsize=9, ha='center', va='top',
            bbox={'boxstyle': "round,pad=0.5", 'facecolor': '#F5F5F5', 'edgecolor': 'gray'})

    plt.tight_layout()
    return fig

if __name__ == "__main__":
    # Create and save the flowchart
    fig = create_cosmicbiomass_flowchart()

    # Save as high-resolution PNG
    plt.savefig('/home/trinkle/Documents/thesis/cosmicbiomass/cosmicbiomass_workflow_flowchart.png',
                dpi=300, bbox_inches='tight', facecolor='white')

    # Save as PDF for publication
    plt.savefig('/home/trinkle/Documents/thesis/cosmicbiomass/cosmicbiomass_workflow_flowchart.pdf',
                bbox_inches='tight', facecolor='white')

    print("✅ CosmicBiomass workflow flowchart created successfully!")
    print("📁 Saved as:")
    print("   • cosmicbiomass_workflow_flowchart.png (high-res)")
    print("   • cosmicbiomass_workflow_flowchart.pdf (publication)")

    plt.show()
