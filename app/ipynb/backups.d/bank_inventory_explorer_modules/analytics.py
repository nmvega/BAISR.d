"""
Analytics and metrics calculation.
"""

import logging
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, HTML

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Calculate and display analytics for bank infrastructure.
    """
    
    def __init__(self):
        """Initialize analytics engine."""
        logger.debug("AnalyticsEngine initialized")
    
    def calculate_metrics(self, data):
        """
        Calculate key metrics from component data.
        
        Args:
            data (dict): Dictionary with DataFrames
            
        Returns:
            dict: Calculated metrics
        """
        metrics = {}
        
        if 'components' not in data or data['components'].empty:
            logger.warning("No component data for analytics")
            return metrics
        
        components_df = data['components']
        
        # Basic counts
        metrics['total_components'] = len(components_df)
        metrics['component_types'] = components_df['component_type'].nunique()
        metrics['locations'] = components_df['physical_location'].nunique()
        
        # Network metrics
        metrics['total_vlans'] = components_df['vlan'].nunique() if 'vlan' in components_df.columns else 0
        metrics['components_with_ip'] = components_df['ip'].notna().sum() if 'ip' in components_df.columns else 0

        # Protocol metrics
        if 'protocol_name' in components_df.columns:
            metrics['unique_protocols'] = components_df['protocol_name'].nunique()
            metrics['unassigned_protocols'] = (components_df['protocol_id'] == 999).sum()

        # MAC address metrics
        if 'mac' in components_df.columns:
            metrics['unique_mac_addresses'] = components_df['mac'].nunique()
            metrics['default_mac_addresses'] = (components_df['mac'] == '00:00:00:00:00:00').sum()

        # Quality grade metrics
        if 'record_quality_grade' in components_df.columns:
            quality_dist = components_df['record_quality_grade'].value_counts()
            metrics['green_records'] = quality_dist.get('_PT_GREEN_RECORD_', 0)
            metrics['yellow_records'] = quality_dist.get('_PT_YELLOW_RECORD_', 0)
            metrics['red_records'] = quality_dist.get('_PT_RED_RECORD_', 0)

        # Relationship metrics
        if 'total_relationship_count' in components_df.columns:
            metrics['avg_connections'] = components_df['total_relationship_count'].mean()
            metrics['max_connections'] = components_df['total_relationship_count'].max()
            metrics['isolated_components'] = (components_df['total_relationship_count'] == 0).sum()
        
        # Dependency metrics
        if 'dependencies' in data and not data['dependencies'].empty:
            deps_df = data['dependencies']
            metrics['total_dependencies'] = len(deps_df)
            metrics['unique_consumers'] = deps_df['component_id'].nunique() if 'component_id' in deps_df.columns else 0
            metrics['unique_producers'] = deps_df['related_component_id'].nunique() if 'related_component_id' in deps_df.columns else 0
        
        # Relationship metrics
        if 'relationships' in data and not data['relationships'].empty:
            rels_df = data['relationships']
            metrics['total_relationships'] = len(rels_df)
            metrics['relationship_types'] = rels_df['relationship_type'].nunique()
        
        logger.info(f"Calculated {len(metrics)} metrics")
        return metrics
    
    def create_metrics_display(self, metrics):
        """
        Create visual display of metrics.
        
        Args:
            metrics (dict): Calculated metrics
            
        Returns:
            widgets.VBox: Metrics display widget
        """
        if not metrics:
            return widgets.HTML(value="<p>No metrics available</p>")
        
        # Create metric cards
        cards_html = """
        <style>
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        </style>
        <div class="metric-grid">
        """
        
        # Key metrics to display
        key_metrics = [
            ('total_components', 'Total Components', '🖥'),
            ('component_types', 'Component Types', '📦'),
            ('locations', 'Locations', '🏢'),
            ('total_vlans', 'VLANs', '🌐'),
            ('unique_protocols', 'Protocols', '🔌'),
            ('total_relationships', 'Relationships', '🤝'),
            ('green_records', 'Quality: Green', '🟢'),
            ('yellow_records', 'Quality: Yellow', '🟡'),
            ('red_records', 'Quality: Red', '🔴')
        ]
        
        for metric_key, label, icon in key_metrics:
            if metric_key in metrics:
                value = metrics[metric_key]
                if isinstance(value, float):
                    value = f"{value:.1f}"
                cards_html += f"""
                <div class="metric-card">
                    <div class="metric-label">{icon} {label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """
        
        cards_html += "</div>"
        
        return widgets.HTML(value=cards_html)
    
    def create_component_distribution(self, data):
        """
        Create component type distribution display.
        
        Args:
            data (dict): Dictionary with DataFrames
            
        Returns:
            widgets.VBox: Distribution display
        """
        if 'components' not in data or data['components'].empty:
            return widgets.HTML(value="<p>No component data</p>")
        
        components_df = data['components']
        
        # Calculate distributions
        type_dist = components_df['component_type'].value_counts()
        location_dist = components_df['physical_location'].value_counts()
        
        # Create HTML tables
        html = """
        <style>
        .dist-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        .dist-table th {
            background-color: #1565C0;
            color: white;
            padding: 10px;
            text-align: left;
        }
        .dist-table td {
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }
        .dist-table tr:hover {
            background-color: #f5f5f5;
        }
        </style>
        """
        
        # Component type distribution
        html += "<h4>📦 Component Type Distribution</h4>"
        html += '<table class="dist-table">'
        html += "<tr><th>Type</th><th>Count</th><th>Percentage</th></tr>"
        
        total = len(components_df)
        for comp_type, count in type_dist.items():
            pct = (count / total) * 100
            html += f"<tr><td>{comp_type}</td><td>{count}</td><td>{pct:.1f}%</td></tr>"
        
        html += "</table>"
        
        # Location distribution
        html += "<h4>🏢 Location Distribution</h4>"
        html += '<table class="dist-table">'
        html += "<tr><th>Location</th><th>Count</th><th>Percentage</th></tr>"
        
        for location, count in location_dist.items():
            pct = (count / total) * 100
            html += f"<tr><td>{location}</td><td>{count}</td><td>{pct:.1f}%</td></tr>"
        
        html += "</table>"
        
        return widgets.HTML(value=html)
    
    def create_health_indicators(self, metrics):
        """
        Create health status indicators.
        
        Args:
            metrics (dict): Calculated metrics
            
        Returns:
            widgets.VBox: Health indicators
        """
        indicators = []
        
        # Check for isolated components
        if 'isolated_components' in metrics:
            isolated = metrics['isolated_components']
            if isolated == 0:
                status = '🔵 All components connected'
                color = 'green'
            else:
                status = f'🔴 {isolated} isolated components'
                color = 'red'
            
            indicators.append(widgets.HTML(
                value=f'<div style="color: {color}; font-weight: bold;">{status}</div>'
            ))
        
        # Check average connections
        if 'avg_connections' in metrics:
            avg = metrics['avg_connections']
            if avg > 3:
                status = '🔵 Good connectivity'
                color = 'green'
            elif avg > 1:
                status = '🟡 Moderate connectivity'
                color = 'orange'
            else:
                status = '🔴 Low connectivity'
                color = 'red'
            
            indicators.append(widgets.HTML(
                value=f'<div style="color: {color}; font-weight: bold;">{status} (avg: {avg:.1f})</div>'
            ))
        
        # Check component coverage
        if 'components_with_ip' in metrics and 'total_components' in metrics:
            with_ip = metrics['components_with_ip']
            total = metrics['total_components']
            pct = (with_ip / total) * 100 if total > 0 else 0
            
            if pct > 90:
                status = '🔵 Good IP coverage'
                color = 'green'
            elif pct > 70:
                status = '🟡 Moderate IP coverage'
                color = 'orange'
            else:
                status = '🔴 Low IP coverage'
                color = 'red'
            
            indicators.append(widgets.HTML(
                value=f'<div style="color: {color}; font-weight: bold;">{status} ({pct:.0f}%)</div>'
            ))
        
        if not indicators:
            indicators.append(widgets.HTML(value="<p>No health data available</p>"))
        
        return widgets.VBox(indicators)


def create_analytics_dashboard(data):
    """
    Create complete analytics dashboard.
    
    Args:
        data (dict): Dictionary with DataFrames
        
    Returns:
        widgets.VBox: Complete dashboard
    """
    engine = AnalyticsEngine()
    
    # Calculate metrics
    metrics = engine.calculate_metrics(data)
    
    # Create dashboard sections
    sections = []
    
    # Header
    sections.append(widgets.HTML(
        value='<h2 style="color: #1565C0; border-bottom: 2px solid #1565C0;">'
              '📊 Analytics Dashboard</h2>'
    ))
    
    # Key metrics
    sections.append(widgets.HTML(value='<h3>🎯 Key Metrics</h3>'))
    sections.append(engine.create_metrics_display(metrics))
    
    # Health indicators
    sections.append(widgets.HTML(value='<h3>🏥 System Health</h3>'))
    sections.append(engine.create_health_indicators(metrics))
    
    # Distributions
    sections.append(widgets.HTML(value='<h3>📊 Distributions</h3>'))
    sections.append(engine.create_component_distribution(data))
    
    return widgets.VBox(
        sections,
        layout=widgets.Layout(
            padding='20px',
            width='100%'
        )
    )