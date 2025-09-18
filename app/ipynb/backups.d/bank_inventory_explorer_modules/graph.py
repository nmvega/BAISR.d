"""
Graph visualization and layout management.
"""

import logging
from .config import COMPONENT_COLORS

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Builds and manages graph visualizations with proper colors and filtering.
    """
    
    def __init__(self):
        """Initialize graph builder."""
        self.component_colors = COMPONENT_COLORS
        logger.debug("GraphBuilder initialized")
    
    def create_graph_data(self, data, sizing_mode='combined', 
                         show_hierarchical=True, show_dependencies=True, show_peer=True):
        """
        Create nodes and edges for the graph visualization.
        
        Args:
            data (dict): Dictionary with components, dependencies, relationships DataFrames
            sizing_mode (str): Node sizing strategy
            show_hierarchical (bool): Show hierarchical relationships
            show_dependencies (bool): Show dependency relationships
            show_peer (bool): Show peer relationships
            
        Returns:
            tuple: (nodes list, edges list)
        """
        if not data or 'components' not in data:
            logger.warning("No component data available")
            return [], []
        
        components_df = data['components']
        relationships_df = data.get('relationships', None)
        
        # Create nodes with PROPER COLORS (BUG FIX!)
        nodes = []
        for _, comp in components_df.iterrows():
            # Debug logging for gray node issue
            comp_id = comp.get('component_id', 'UNKNOWN')
            comp_name = comp.get('fqdn', '')
            comp_type = comp.get('component_type', '')
            comp_location = comp.get('physical_location', '')
            
            if not comp_name or not comp_type:
                logger.warning(f"Missing data for component {comp_id}: fqdn='{comp_name}', type='{comp_type}', location='{comp_location}'")
            
            # Create label - extract short name from FQDN
            fqdn_parts = comp_name.split('.')
            short_name = fqdn_parts[0] if fqdn_parts else comp_name
            label = f"{short_name}.{comp_location}"
            
            # GET CORRECT COLOR FROM PALETTE (CRITICAL BUG FIX!)
            component_type = comp['component_type']
            color = self.component_colors.get(component_type, '#757575')
            
            # Log if using default gray color
            if color == '#757575':
                logger.info(f"Component {comp_id} using default gray - type '{component_type}' not in color palette")
            
            # Calculate node size
            node_size = self._calculate_node_size(comp, sizing_mode)
            
            node = {
                'data': {
                    'id': str(comp['component_id']),
                    'label': label,
                    'name': comp.get('fqdn', ''),
                    'app_code': comp.get('app_code', ''),
                    'type': component_type,
                    'subtype': comp.get('component_subtype', ''),
                    'ip': comp.get('ip', ''),
                    'mac': comp.get('mac', ''),
                    'location': comp['physical_location'],
                    'vlan': comp.get('vlan', ''),
                    'port': comp.get('port', ''),
                    'protocol': comp.get('protocol_name', ''),
                    'quality': comp.get('record_quality_grade', ''),
                    'connections': comp.get('total_relationship_count', 0),
                    'size': node_size,
                    'bgColor': color,  # Move color to data for data-driven styling
                    # FK IDs for tooltips
                    'component_id': comp.get('component_id'),
                    'type_id': comp.get('component_type_id'),
                    'subtype_id': comp.get('component_subtype_id'),
                    'location_id': comp.get('physical_location_id'),
                    'protocol_id': comp.get('protocol_id'),
                    'environment_id': comp.get('environment_id')
                },
                'style': {
                    'border-width': 2,
                    'border-color': '#000000',
                    'border-style': 'solid',
                    'color': '#ffffff',
                    'text-outline-width': 2,
                    'text-outline-color': '#000000',
                    'width': f'{node_size}px',
                    'height': f'{node_size}px',
                    'font-size': '10px'
                }
            }
            nodes.append(node)
        
        logger.info(f"Created {len(nodes)} nodes with sizing mode: {sizing_mode}")
        
        # Create edges
        edges = []

        # All relationships (including all 14 types from schema)
        if relationships_df is not None:
            # Define all dependency-type relationships from schema
            dependency_types = (
                'replicates_from', 'fails_over_to', 'consumes_api_from',
                'persists_to', 'publishes_to', 'subscribes_to', 'proxied_by',
                'authenticates_via', 'monitors'
            )

            # Peer/collaboration relationships
            peer_types = (
                'collaborates_with', 'peers_with', 'vm_guest_of',
                'load_balanced_by', 'communicates_with'
            )

            dep_count = 0
            peer_count = 0

            for _, rel in relationships_df.iterrows():
                rel_type = rel.get('relationship_type', '')

                # Check if it's a dependency-type relationship
                if show_dependencies and rel_type in dependency_types:
                    edge = self._create_dependency_edge(rel)
                    edges.append(edge)
                    dep_count += 1
                # Otherwise check if it's a peer relationship
                elif show_peer and rel_type in peer_types:
                    edge = self._create_peer_edge(rel)
                    edges.append(edge)
                    peer_count += 1

            logger.debug(f"Created {dep_count} dependency edges, {peer_count} peer edges")
        
        logger.info(f"Created graph with {len(nodes)} nodes and {len(edges)} edges")
        return nodes, edges
    
    def apply_search_filter(self, nodes, search_term):
        """
        Apply search filter to highlight matching nodes.
        
        Args:
            nodes (list): List of node dictionaries
            search_term (str): Search term
            
        Returns:
            list: Modified nodes with highlighting
        """
        if not search_term:
            return nodes
        
        search_lower = search_term.lower()
        
        for node in nodes:
            node_data = node['data']
            
            # Check if node matches search
            matches = (
                search_lower in node_data.get('name', '').lower() or
                search_lower in node_data.get('ip', '').lower() or
                search_lower in str(node_data.get('vlan', '')).lower() or
                search_lower in node_data.get('location', '').lower()
            )
            
            if matches:
                # Highlight matching nodes
                node['style']['border-color'] = '#FFD700'
                node['style']['border-width'] = 4
            else:
                # Fade non-matching nodes
                node['style']['opacity'] = 0.3
        
        return nodes
    
    def apply_neighborhood_filter(self, nodes, edges, search_term):
        """
        Filter to show only searched node and its directly connected neighbors.
        
        Args:
            nodes (list): List of node dictionaries
            edges (list): List of edge dictionaries
            search_term (str): Search term
            
        Returns:
            tuple: (filtered_nodes, filtered_edges)
        """
        if not search_term:
            return nodes, edges
        
        search_lower = search_term.lower()
        
        # Find matching node IDs
        matched_ids = set()
        for node in nodes:
            node_data = node['data']
            if (search_lower in node_data.get('name', '').lower() or
                search_lower in node_data.get('ip', '').lower() or
                search_lower in str(node_data.get('vlan', '')).lower() or
                search_lower in node_data.get('location', '').lower()):
                matched_ids.add(node_data['id'])
        
        if not matched_ids:
            # No matches, return original
            return nodes, edges
        
        # Find all connected node IDs
        connected_ids = matched_ids.copy()
        for edge in edges:
            source = edge['data']['source']
            target = edge['data']['target']
            
            if source in matched_ids:
                connected_ids.add(target)
            if target in matched_ids:
                connected_ids.add(source)
        
        # Filter nodes to neighborhood only
        filtered_nodes = []
        for node in nodes:
            if node['data']['id'] in connected_ids:
                # Highlight searched nodes
                if node['data']['id'] in matched_ids:
                    node['style']['border-color'] = '#FFD700'
                    node['style']['border-width'] = 4
                filtered_nodes.append(node)
        
        # Filter edges to neighborhood only
        filtered_edges = []
        for edge in edges:
            if (edge['data']['source'] in connected_ids and 
                edge['data']['target'] in connected_ids):
                filtered_edges.append(edge)
        
        logger.info(f"Neighborhood filter: {len(filtered_nodes)} nodes, {len(filtered_edges)} edges")
        return filtered_nodes, filtered_edges
    
    def _calculate_node_size(self, component, sizing_mode):
        """Calculate node size based on sizing mode."""
        base_size = 20
        size_multiplier = 2
        max_size = 60
        
        if sizing_mode == 'uniform':
            return 30
        elif sizing_mode == 'hierarchical':
            count = component.get('child_count', 0)
        elif sizing_mode == 'dependencies':
            count = (component.get('relationship_from_count', 0) + 
                    component.get('relationship_to_count', 0))
        elif sizing_mode == 'peer':
            count = component.get('peer_relationship_count', 0)
        else:  # combined
            count = component.get('total_relationship_count', 0)
        
        return min(base_size + (count * size_multiplier), max_size)
    
    def _create_hierarchical_edge(self, comp):
        """Create hierarchical edge."""
        return {
            'data': {
                'id': f"hier_{comp.get('parent_component_id', 0)}_{comp['component_id']}",
                'source': str(comp.get('parent_component_id', 0)),
                'target': str(comp['component_id']),
                'type': 'hierarchical',
                'label': 'parent→child'
            },
            'style': {
                'line-color': '#424242',
                'line-style': 'solid',
                'target-arrow-color': '#424242',
                'target-arrow-shape': 'triangle',
                'width': 2,
                'curve-style': 'straight'
            }
        }
    
    def _create_dependency_edge(self, rel):
        """Create dependency edge."""
        return {
            'data': {
                'id': f"dep_{rel['component_id']}_{rel['related_component_id']}",
                'source': str(rel['component_id']),
                'target': str(rel['related_component_id']),
                'type': 'dependency',
                'label': rel.get('relationship_type', 'dependency')
            },
            'style': {
                'line-color': '#616161',
                'line-style': 'dashed',
                'target-arrow-color': '#616161',
                'target-arrow-shape': 'triangle',
                'width': 2,
                'curve-style': 'straight'
            }
        }
    
    def _create_peer_edge(self, rel):
        """Create peer relationship edge."""
        return {
            'data': {
                'id': f"peer_{rel['component_id']}_{rel['related_component_id']}",
                'source': str(rel['component_id']),
                'target': str(rel['related_component_id']),
                'type': 'peer',
                'label': rel.get('relationship_type', 'peer')
            },
            'style': {
                'line-color': '#757575',
                'line-style': 'dotted',
                'width': 2,
                'curve-style': 'straight'
            }
        }
    
    def get_layout_config(self, layout_name):
        """
        Get layout configuration for cytoscape.
        
        Args:
            layout_name (str): Layout algorithm name
            
        Returns:
            dict: Layout configuration
        """
        configs = {
            'dagre': {
                'name': 'dagre',
                'rankDir': 'TB',
                'spacingFactor': 1.5
            },
            'cose': {
                'name': 'cose',
                'idealEdgeLength': 100,
                'nodeOverlap': 20
            },
            'circle': {
                'name': 'circle'
            },
            'grid': {
                'name': 'grid'
            }
        }
        
        config = configs.get(layout_name, {'name': layout_name})
        logger.debug(f"Using layout: {layout_name}")
        return config


def get_graph_styles():
    """
    Get cytoscape style definitions.
    
    Returns:
        list: Style definitions for cytoscape
    """
    return [
        {
            'selector': 'node',
            'style': {
                'content': 'data(label)',
                'text-valign': 'center',
                'text-halign': 'center',
                'font-family': 'Arial, sans-serif',
                'font-weight': 'bold',
                'background-color': 'data(bgColor)'  # Data-driven color
            }
        },
        {
            'selector': 'edge',
            'style': {
                'content': 'data(label)',
                'font-size': '8px',
                'text-rotation': 'autorotate',
                'text-margin-y': -10
            }
        }
    ]