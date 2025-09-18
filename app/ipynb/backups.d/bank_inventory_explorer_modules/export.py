"""
Export functionality for data, graphs, and visualizations.
"""

import base64
import json
import logging
import pandas as pd
from io import StringIO, BytesIO
import ipywidgets as widgets
from IPython.display import Javascript, display

logger = logging.getLogger(__name__)


def export_to_csv(dataframe, filename='export.csv'):
    """
    Export DataFrame to CSV with download link.
    
    Args:
        dataframe (pd.DataFrame): Data to export
        filename (str): Output filename
        
    Returns:
        widgets.HTML: Download link widget
    """
    if dataframe is None or dataframe.empty:
        logger.warning("No data to export")
        return widgets.HTML(value="<p>No data to export</p>")
    
    try:
        # Convert DataFrame to CSV
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        
        # Encode to base64
        b64 = base64.b64encode(csv_string.encode()).decode()
        
        # Create download link
        href = f'<a href="data:text/csv;base64,{b64}" download="{filename}">📥 Download {filename}</a>'
        
        logger.info(f"CSV export prepared: {filename} ({len(dataframe)} rows)")
        return widgets.HTML(value=href)
        
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        return widgets.HTML(value="<p style='color:red'>Export failed</p>")


def export_graph_to_json(graph_data, filename='graph.json'):
    """
    Export graph data to JSON format.
    
    Args:
        graph_data (dict): Graph data with nodes and edges
        filename (str): Output filename
        
    Returns:
        widgets.HTML: Download link widget
    """
    try:
        # Convert to JSON
        json_string = json.dumps(graph_data, indent=2)
        
        # Encode to base64
        b64 = base64.b64encode(json_string.encode()).decode()
        
        # Create download link
        href = f'<a href="data:application/json;base64,{b64}" download="{filename}">💾 Download {filename}</a>'
        
        logger.info(f"JSON export prepared: {filename}")
        return widgets.HTML(value=href)
        
    except Exception as e:
        logger.error(f"JSON export failed: {e}")
        return widgets.HTML(value="<p style='color:red'>Export failed</p>")


def trigger_graph_png_export(cyto_widget, filename='graph.png'):
    """
    Trigger PNG export from ipycytoscape widget.
    
    Args:
        cyto_widget: ipycytoscape.CytoscapeWidget instance
        filename (str): Output filename
    """
    try:
        # Use ipycytoscape's built-in PNG export
        # This triggers a browser download
        cyto_widget.download_image(filename, format='png')
        logger.info(f"PNG export triggered: {filename}")
        
    except Exception as e:
        logger.error(f"PNG export failed: {e}")
        raise


def create_export_controls(data, graph_widget=None):
    """
    Create export control panel with all export options.
    
    Args:
        data (dict): Dictionary with DataFrames
        graph_widget: Optional ipycytoscape widget for PNG export
        
    Returns:
        widgets.VBox: Export control panel
    """
    exports = []
    
    # CSV exports for each table
    if 'components' in data and not data['components'].empty:
        csv_link = export_to_csv(data['components'], 'components.csv')
        exports.append(widgets.HTML(value="<h4>📊 Table Exports</h4>"))
        exports.append(csv_link)
    
    if 'relationships' in data and not data['relationships'].empty:
        csv_link = export_to_csv(data['relationships'], 'relationships.csv')
        exports.append(csv_link)
    
    # Graph exports
    if graph_widget:
        exports.append(widgets.HTML(value="<h4>🌐 Graph Exports</h4>"))
        
        # PNG export button
        png_button = widgets.Button(
            description='📷 Export PNG',
            button_style='success',
            layout=widgets.Layout(width='150px')
        )
        
        def on_png_click(b):
            try:
                trigger_graph_png_export(graph_widget)
                logger.info("PNG export initiated")
            except Exception as e:
                logger.error(f"PNG export error: {e}")
        
        png_button.on_click(on_png_click)
        exports.append(png_button)
        
        # JSON export for graph state
        if hasattr(graph_widget, 'graph'):
            graph_data = {
                'nodes': graph_widget.graph.nodes,
                'edges': graph_widget.graph.edges
            }
            json_link = export_graph_to_json(graph_data, 'graph_state.json')
            exports.append(json_link)
    
    return widgets.VBox(
        exports,
        layout=widgets.Layout(
            padding='10px',
            border='1px solid #ddd',
            border_radius='5px'
        )
    )


def export_summary_report(data, filename='summary_report.csv'):
    """
    Export summary statistics report.
    
    Args:
        data (dict): Dictionary with DataFrames
        filename (str): Output filename
        
    Returns:
        widgets.HTML: Download link widget
    """
    try:
        summary_data = []
        
        if 'components' in data:
            df = data['components']
            
            # Component type counts
            type_counts = df['component_type'].value_counts()
            for comp_type, count in type_counts.items():
                summary_data.append({
                    'Category': 'Component Type',
                    'Item': comp_type,
                    'Count': count
                })
            
            # Location counts
            location_counts = df['physical_location'].value_counts()
            for location, count in location_counts.items():
                summary_data.append({
                    'Category': 'Location',
                    'Item': location,
                    'Count': count
                })
        
        # Create summary DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        return export_to_csv(summary_df, filename)
        
    except Exception as e:
        logger.error(f"Summary export failed: {e}")
        return widgets.HTML(value="<p style='color:red'>Export failed</p>")