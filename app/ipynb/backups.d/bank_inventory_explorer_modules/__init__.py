"""
Bank Application Inventory System - Jupyter Notebook Modules
=============================================================

Modular components for the interactive Jupyter notebook explorer.
Provides clean separation of concerns for maintainability and reusability.

Modules:
--------
- database: PostgreSQL connection management with schema awareness
- config: Configuration and environment variable handling
- data_ops: Data loading, caching, and transformation
- graph: Graph visualization and layout management
- widgets: UI component factories and state management
- export: Export utilities for CSV, PNG, JSON formats
- analytics: Metrics calculation and analysis
- erd: Entity Relationship Diagram generation

Version: 3.0 - Complete rewrite with bug fixes
"""

__version__ = "3.0.0"
__author__ = "Bank Application Inventory System Team"

# Make key components easily importable
from .database import DatabaseConnection
from .config import get_config, get_component_colors, COMPONENT_COLORS
from .data_ops import DataManager, prepare_table_displays
from .graph import GraphBuilder, get_graph_styles
from .widgets import (
    create_schema_selector, 
    create_status_indicator, 
    create_refresh_button,
    create_export_button, 
    create_layout_selector, 
    create_sizing_selector,
    create_search_box, 
    create_filter_checkboxes, 
    create_section_header,
    create_output_area, 
    create_tabbed_tables,
    create_graph_container,
    create_control_panel,
    WidgetManager
)
from .export import (
    export_to_csv,
    export_graph_to_json,
    trigger_graph_png_export,
    create_export_controls,
    export_summary_report
)
from .analytics import AnalyticsEngine, create_analytics_dashboard
from .erd import ERDGenerator, create_erd_section

__all__ = [
    'DatabaseConnection',
    'get_config', 
    'get_component_colors',
    'COMPONENT_COLORS',
    'DataManager',
    'prepare_table_displays',
    'GraphBuilder',
    'get_graph_styles',
    'create_schema_selector',
    'create_status_indicator',
    'create_refresh_button',
    'create_export_button',
    'create_layout_selector',
    'create_sizing_selector',
    'create_search_box',
    'create_filter_checkboxes',
    'create_section_header',
    'create_output_area',
    'create_tabbed_tables',
    'create_graph_container',
    'create_control_panel',
    'WidgetManager',
    'export_to_csv',
    'export_graph_to_json',
    'trigger_graph_png_export',
    'create_export_controls',
    'export_summary_report',
    'AnalyticsEngine',
    'create_analytics_dashboard',
    'ERDGenerator',
    'create_erd_section'
]