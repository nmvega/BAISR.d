#!/usr/bin/env python3
"""
Bank Application Inventory System (BAIS) - Streamlit Application V6 - Permanent Shadows
Correct implementation with:
- Sidebar navigation (NOT top tabs)
- Main page filters (NOT in sidebar)
- Explorer page with THREE VERTICALLY STACKED synchronized views
- Anti-flat blue/white theme with ALL CAPS labels
"""

import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import networkx as nx
import json
import base64
from datetime import datetime
from io import StringIO, BytesIO
import sys
import os
import tempfile

# Add the ipynb modules to path to reuse existing database module
sys.path.append(os.path.join(os.path.dirname(__file__), 'ipynb'))
from bank_inventory_explorer_modules.database import DatabaseConnection

# Import ERD generator
try:
    from eralchemy2 import render_er
    HAS_ERALCHEMY = True
except ImportError:
    HAS_ERALCHEMY = False

# ============================================================================
# CONFIGURATION
# ============================================================================

# Page config must be first Streamlit command
st.set_page_config(
    page_title="BAIS - Bank Application Inventory System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Component colors matching the notebook
COMPONENT_COLORS = {
    'application': '#2E7D32',
    'polyglot_persistence': '#1565C0',
    'block_level_persistence': '#E65100',
    'networking': '#B71C1C',
    '_PT_PENDING_': '#FFC107',
    '_PT_NO_DATA_FOUND_': '#9E9E9E'
}

# Quality grade indicators
QUALITY_INDICATORS = {
    '_PT_GREEN_RECORD_': '🟢',
    '_PT_YELLOW_RECORD_': '🟡',
    '_PT_RED_RECORD_': '🔴'
}

# ============================================================================
# CUSTOM CSS - ANTI-FLAT BLUE/WHITE THEME WITH ALL CAPS
# ============================================================================

CUSTOM_CSS = """
<style>
    /* ========== MAIN APP STYLING ========== */
    .stApp {
        background-color: #FFEDD4;
    }

    /* All text dark blue */
    .stApp p, .stApp span, .stApp div, .stApp label {
        color: #0D47A1 !important;
    }

    /* Headers with consistent 4px borders */
    h1, h2, h3, h4, h5, h6 {
        color: #1565C0 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        border-bottom: 4px solid #0D47A1 !important;
        padding-bottom: 5px !important;
        margin-bottom: 10px !important;
        margin-top: 10px !important;
    }

    /* ========== SIDEBAR STYLING - ENHANCED ========== */
    section[data-testid="stSidebar"] {
        background-color: #E3F2FD;
        border-right: 4px solid #0D47A1;
    }

    /* Sidebar title container */
    section[data-testid="stSidebar"] > div {
        padding: 10px !important;
    }

    /* COMPLETELY REMOVE ALL RADIO BUTTON CIRCLES */

    /* Target Streamlit's specific radio button structure */
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* Hide circles in sidebar navigation */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    /* Hide the actual input elements */
    input[type="radio"] {
        display: none !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
    }

    /* Hide any remaining radio indicators */
    .stRadio > div > label > div:first-child,
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    /* Fix Navigation label - make it non-interactive header style */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > label:first-child {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #0D47A1 !important;
        text-transform: uppercase !important;
        margin-bottom: 10px !important;
        display: block !important;
        cursor: default !important;
        pointer-events: none !important;
    }

    /* Sidebar navigation container - NO BORDER, sleeker design */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] {
        border: none !important;
        padding: 0 !important;
        background-color: transparent !important;
        margin-bottom: 20px !important;
    }

    /* Navigation items - THINNER buttons with MORE SPACING */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        padding: 3px 12px !important;
        margin: 6px 0 !important;
        display: block !important;
        width: 100% !important;
        text-transform: uppercase !important;
        color: #0D47A1 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        background-color: white !important;
        border: 1px solid #90CAF9 !important;
        border-radius: 4px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        line-height: 1.2 !important;
    }

    /* Hover effect for navigation items - ENHANCED shadow */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background-color: #F5F5F5 !important;
        border-color: #1565C0 !important;
        transform: translateX(2px) !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
    }

    /* Selected navigation item - light gray background WITH STRONGER SHADOW */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
        background-color: #E0E0E0 !important;
        color: #0D47A1 !important;
        border-color: #0D47A1 !important;
        border-width: 2px !important;
        font-weight: 700 !important;
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2) !important;
    }

    /* Sidebar headers and info boxes - NO BORDERS, ONLY FOR SYSTEM INFO */
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        background-color: transparent !important;
        margin-bottom: 15px !important;
        box-shadow: none !important;
    }

    /* Only style the SYSTEM INFO alert box */
    section[data-testid="stSidebar"] .stAlert {
        border: 2px solid #0D47A1 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        background-color: white !important;
        box-shadow: 0 3px 8px rgba(13, 71, 161, 0.15) !important;
    }

    /* Ensure no nested borders anywhere */
    section[data-testid="stSidebar"] * {
        border: none !important;
    }

    /* Re-enable borders ONLY for navigation buttons - 4px BORDER */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        border: 4px solid #0D47A1 !important;
    }

    /* Re-enable border for selected items - KEEP 4px */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
        border: 4px solid #0D47A1 !important;
    }

    /* Re-enable border for alert box */
    section[data-testid="stSidebar"] .stAlert {
        border: 2px solid #0D47A1 !important;
    }

    /* ========== INPUT ELEMENTS - CONSISTENT 4px BORDERS WITH PERMANENT SHADOW ========== */
    .stTextInput > div > div > input {
        background-color: white !important;
        border: 4px solid #0D47A1 !important;
        border-radius: 8px !important;
        color: #0D47A1 !important;
        font-weight: 500;
        box-shadow: 0 2px 6px rgba(13, 71, 161, 0.15) !important;
    }

    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: white !important;
        border: 4px solid #0D47A1 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 6px rgba(13, 71, 161, 0.15) !important;
    }

    /* ========== BUTTONS WITH PERMANENT SHADOW AND ENHANCED HOVER ========== */
    .stButton > button {
        background-color: white !important;
        border: 4px solid #0D47A1 !important;
        border-radius: 8px !important;
        color: #0D47A1 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        padding: 8px 20px;
        transition: all 0.3s ease;
        box-shadow: 0 3px 8px rgba(13, 71, 161, 0.2) !important;
    }

    .stButton > button:hover {
        background-color: #E3F2FD !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(13, 71, 161, 0.35) !important;
    }

    .stDownloadButton > button {
        background-color: #0D47A1 !important;
        color: white !important;
        border: 4px solid #0D47A1 !important;
        border-radius: 8px !important;
        text-transform: uppercase !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 8px rgba(13, 71, 161, 0.3) !important;
    }

    /* ========== METRICS WITH PERMANENT SHADOW AND HOVER EFFECT ========== */
    div[data-testid="metric-container"] {
        background-color: white !important;
        border: 4px solid #0D47A1 !important;
        border-radius: 10px !important;
        padding: 12px !important;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.25) !important;
        margin-bottom: 10px !important;
        transition: all 0.3s ease !important;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 20px rgba(13, 71, 161, 0.35) !important;
    }

    div[data-testid="metric-container"] label {
        text-transform: uppercase !important;
        color: #0D47A1 !important;
        font-weight: 700 !important;
    }

    /* ========== TABLES - WHITE BACKGROUNDS ========== */
    /* Main dataframe container WITH PERMANENT SHADOW and hover */
    div[data-testid="stDataFrame"] {
        border: 4px solid #0D47A1 !important;
        border-radius: 10px !important;
        padding: 5px !important;
        background-color: white !important;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.2) !important;
        margin-bottom: 1rem !important;
        transition: all 0.3s ease !important;
    }

    div[data-testid="stDataFrame"]:hover {
        box-shadow: 0 8px 20px rgba(13, 71, 161, 0.3) !important;
    }

    /* Remove internal borders */
    div[data-testid="stDataFrame"] > div {
        border: none !important;
    }

    /* Table headers - LIGHT blue background, dark blue text */
    div[data-testid="stDataFrame"] thead th {
        background-color: #E3F2FD !important;
        color: #0D47A1 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        text-transform: uppercase !important;
        border-bottom: 2px solid #0D47A1 !important;
        padding: 10px !important;
        text-align: left !important;
    }

    /* Table cells - WHITE background */
    div[data-testid="stDataFrame"] tbody td {
        color: #0D47A1 !important;
        background-color: white !important;
        border-bottom: 1px solid #E3F2FD !important;
        border-right: 1px solid #E3F2FD !important;
        padding: 8px !important;
        font-weight: 500 !important;
        font-size: 16px !important;
    }

    /* Alternate rows - very light blue */
    div[data-testid="stDataFrame"] tbody tr:nth-child(even) td {
        background-color: #F8FBFF !important;
    }

    /* Hover effect */
    div[data-testid="stDataFrame"] tbody tr:hover td {
        background-color: #E3F2FD !important;
        cursor: pointer;
    }

    /* Fix Glide data editor */
    .glideDataEditor {
        border: 4px solid #0D47A1 !important;
        border-radius: 8px !important;
        background-color: white !important;
    }

    /* Fix dataframe class tables */
    .dataframe {
        border: 4px solid #0D47A1 !important;
        border-radius: 10px !important;
        overflow: hidden;
        background-color: white !important;
    }

    .dataframe thead th {
        background-color: #E3F2FD !important;
        color: #0D47A1 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        text-transform: uppercase !important;
        border-bottom: 2px solid #0D47A1 !important;
    }

    .dataframe td {
        color: #0D47A1 !important;
        background-color: white !important;
        border: 1px solid #E3F2FD !important;
        font-size: 16px !important;
    }

    /* ========== CHARTS WITH PERMANENT SHADOW AND HOVER EFFECT ========== */
    div[data-testid="stPlotlyChart"] {
        border: 4px solid #0D47A1 !important;
        border-radius: 10px !important;
        padding: 10px !important;
        background-color: white !important;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.2) !important;
        transition: all 0.3s ease !important;
    }

    div[data-testid="stPlotlyChart"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 24px rgba(13, 71, 161, 0.3) !important;
    }

    div[data-testid="stPlotlyChart"] > div {
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    /* ========== ALERTS & INFO BOXES WITH PERMANENT SHADOW ========== */
    .stAlert {
        background-color: #E3F2FD !important;
        border: 4px solid #0D47A1 !important;
        border-radius: 10px !important;
        color: #0D47A1 !important;
        box-shadow: 0 3px 10px rgba(13, 71, 161, 0.2) !important;
    }

    /* ========== LAYOUT ADJUSTMENTS ========== */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }

    /* Hide separators */
    hr {
        display: none !important;
    }

    /* ALL LABELS UPPERCASE */
    label {
        text-transform: uppercase !important;
        color: #0D47A1 !important;
        font-weight: 600 !important;
    }

    /* ========== COMPREHENSIVE HOVER EFFECTS FOR ALL ELEMENTS ========== */

    /* Add hover to ALL interactive elements */
    * {
        transition: all 0.2s ease !important;
    }

    /* Text inputs hover */
    .stTextInput > div > div > input:hover {
        border-color: #0D47A1 !important;
        box-shadow: 0 2px 8px rgba(13, 71, 161, 0.2) !important;
    }

    /* Select boxes hover */
    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover {
        border-color: #0D47A1 !important;
        box-shadow: 0 2px 8px rgba(13, 71, 161, 0.2) !important;
    }

    /* Checkbox hover */
    .stCheckbox:hover {
        transform: scale(1.02) !important;
    }

    /* Radio buttons hover */
    .stRadio > div > label:hover {
        transform: scale(1.02) !important;
        color: #1565C0 !important;
    }

    /* Hide ALL radio button circles everywhere */
    input[type="radio"] {
        display: none !important;
    }

    /* Any clickable element hover effect */
    [role="button"]:hover,
    [cursor="pointer"]:hover {
        filter: brightness(0.95) !important;
        transform: scale(1.01) !important;
    }

    /* Links hover */
    a:hover {
        color: #1565C0 !important;
        text-decoration: underline !important;
    }

    /* Table rows already have hover, but enhance it */
    tbody tr:hover {
        transform: translateX(2px) !important;
        box-shadow: 0 2px 4px rgba(13, 71, 161, 0.1) !important;
    }

    /* Expander hover */
    .streamlit-expanderHeader:hover {
        background-color: #F5F5F5 !important;
        transform: scale(1.01) !important;
    }

    /* Tabs hover */
    .stTabs > div > div > button:hover {
        background-color: #F5F5F5 !important;
        transform: translateY(-1px) !important;
    }
</style>
"""

# ============================================================================
# DATABASE & DATA FUNCTIONS
# ============================================================================

@st.cache_resource
def init_database():
    """Initialize database connection (cached)."""
    db = DatabaseConnection()
    if db.connect():
        db.set_schema('demo')
        return db
    else:
        st.error("❌ Failed to connect to database. Check your .env file.")
        return None

@st.cache_data(ttl=300)
def load_components(_db):
    """Load components data with caching."""
    query = """
    SELECT
        c.*,
        ct.type_name as component_type,
        cs.subtype_name as component_subtype,
        ce.environment_name as environment,
        cpl.location_name as physical_location,
        cos.status_name as ops_status,
        cal.level_name as abstraction_level,
        cp.protocol_name as protocol_name,
        COALESCE(rels_from.from_count, 0) as relationship_from_count,
        COALESCE(rels_to.to_count, 0) as relationship_to_count,
        (COALESCE(rels_from.from_count, 0) + COALESCE(rels_to.to_count, 0)) as total_relationship_count
    FROM {{SCHEMA}}.biz_components c
    LEFT JOIN {{SCHEMA}}.component_types ct ON c.component_type_id = ct.component_type_id
    LEFT JOIN {{SCHEMA}}.component_subtypes cs ON c.component_subtype_id = cs.component_subtype_id
    LEFT JOIN {{SCHEMA}}.component_environments ce ON c.environment_id = ce.environment_id
    LEFT JOIN {{SCHEMA}}.component_physical_locations cpl ON c.physical_location_id = cpl.physical_location_id
    LEFT JOIN {{SCHEMA}}.component_ops_statuses cos ON c.ops_status_id = cos.ops_status_id
    LEFT JOIN {{SCHEMA}}.component_abstraction_levels cal ON c.abstraction_level_id = cal.abstraction_level_id
    LEFT JOIN {{SCHEMA}}.component_protocols cp ON c.protocol_id = cp.protocol_id
    LEFT JOIN (
        SELECT component_id, COUNT(*) as from_count
        FROM {{SCHEMA}}.biz_component_relationships
        GROUP BY component_id
    ) rels_from ON c.component_id = rels_from.component_id
    LEFT JOIN (
        SELECT related_component_id, COUNT(*) as to_count
        FROM {{SCHEMA}}.biz_component_relationships
        GROUP BY related_component_id
    ) rels_to ON c.component_id = rels_to.related_component_id
    ORDER BY c.fqdn;
    """
    return _db.get_dataframe(query)

@st.cache_data(ttl=300)
def load_relationships(_db):
    """Load relationships data with enriched information."""
    query = """
    SELECT
        r.relationship_id,
        c1.fqdn as component_1,
        ct1.type_name as component_1_type,
        rt.type_name as relationship_type,
        c2.fqdn as component_2,
        ct2.type_name as component_2_type,
        r.description,
        r.component_id,
        r.related_component_id,
        r.created_at,
        r.created_by,
        r.updated_at,
        r.updated_by
    FROM {{SCHEMA}}.biz_component_relationships r
    JOIN {{SCHEMA}}.biz_components c1 ON r.component_id = c1.component_id
    JOIN {{SCHEMA}}.biz_components c2 ON r.related_component_id = c2.component_id
    JOIN {{SCHEMA}}.component_types ct1 ON c1.component_type_id = ct1.component_type_id
    JOIN {{SCHEMA}}.component_types ct2 ON c2.component_type_id = ct2.component_type_id
    JOIN {{SCHEMA}}.component_relationship_types rt ON r.relationship_type_id = rt.relationship_type_id
    ORDER BY c1.fqdn, rt.type_name, c2.fqdn;
    """
    return _db.get_dataframe(query)

# ============================================================================
# FILTER FUNCTIONS
# ============================================================================

def apply_filters(components_df, relationships_df, search_term, env_filter, status_filter, type_filter):
    """Apply all filters to dataframes and return filtered versions.

    IMPORTANT: When filtering, we show:
    1. The components that match the filter criteria
    2. ALL components that have relationships with the filtered components (1-hop neighbors)
    This allows users to see the full context of how filtered components interact with the system.
    """

    # Start with copies
    filtered_components = components_df.copy()
    original_components_df = components_df.copy()

    # Apply search filter
    if search_term:
        search_lower = search_term.lower()
        filtered_components = filtered_components[
            filtered_components['fqdn'].astype(str).str.lower().str.contains(search_lower, na=False) |
            filtered_components['app_code'].astype(str).str.lower().str.contains(search_lower, na=False) |
            filtered_components['component_type'].astype(str).str.lower().str.contains(search_lower, na=False)
        ]

    # Apply environment filter
    if env_filter:
        filtered_components = filtered_components[filtered_components['environment'].isin(env_filter)]

    # Apply status filter
    if status_filter:
        filtered_components = filtered_components[filtered_components['ops_status'].isin(status_filter)]

    # Apply type filter
    if type_filter:
        filtered_components = filtered_components[filtered_components['component_type'].isin(type_filter)]

    # Get the IDs of filtered components
    filtered_component_ids = set(filtered_components['component_id'].values)

    # Find all relationships where at least one component is in the filtered set
    # This gives us all connections FROM or TO the filtered components
    filtered_relationships = relationships_df[
        (relationships_df['component_id'].isin(filtered_component_ids)) |
        (relationships_df['related_component_id'].isin(filtered_component_ids))
    ]

    # Now expand the component set to include all connected components (1-hop neighbors)
    connected_component_ids = set()
    connected_component_ids.update(filtered_relationships['component_id'].values)
    connected_component_ids.update(filtered_relationships['related_component_id'].values)

    # Get all components that are either filtered or connected to filtered components
    all_visible_components = original_components_df[
        original_components_df['component_id'].isin(connected_component_ids)
    ]

    # If no filters applied or no connections found, return the filtered components as is
    if len(all_visible_components) == 0:
        all_visible_components = filtered_components
        # Also need to refilter relationships for this case
        filtered_relationships = relationships_df[
            (relationships_df['component_id'].isin(filtered_component_ids)) &
            (relationships_df['related_component_id'].isin(filtered_component_ids))
        ]

    return all_visible_components, filtered_relationships

# ============================================================================
# GRAPH CREATION
# ============================================================================

def create_network_graph(components_df, relationships_df, layout_type='CIRCULAR'):
    """Create network graph using Plotly."""

    # Create networkx graph
    G = nx.Graph()

    # Add nodes
    for _, comp in components_df.iterrows():
        fqdn_parts = str(comp['fqdn']).split('.')
        short_name = fqdn_parts[0] if fqdn_parts else str(comp['fqdn'])

        G.add_node(
            comp['component_id'],
            label=f"{short_name}\n{comp['physical_location']}",
            type=comp['component_type'],
            fqdn=comp['fqdn'],
            app_code=comp['app_code'],
            location=comp['physical_location'],
            connections=comp['total_relationship_count'],
            quality=comp['record_quality_grade'],
            color=COMPONENT_COLORS.get(comp['component_type'], '#757575')
        )

    # Add edges
    for _, rel in relationships_df.iterrows():
        if rel['component_id'] in G.nodes() and rel['related_component_id'] in G.nodes():
            G.add_edge(
                rel['component_id'],
                rel['related_component_id'],
                relationship=rel['relationship_type']
            )

    # Get layout based on selection
    if layout_type == 'HIERARCHICAL':
        try:
            pos = nx.kamada_kawai_layout(G)
        except:
            pos = nx.spring_layout(G, k=2, iterations=50)
    elif layout_type == 'FORCE-DIRECTED':
        pos = nx.spring_layout(G, k=1, iterations=50)
    else:  # CIRCULAR (default)
        pos = nx.circular_layout(G)

    # Create Plotly traces
    edge_trace = go.Scatter(
        x=[], y=[], mode='lines',
        line=dict(width=1, color='#888'),
        hoverinfo='none'
    )

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)

    # Node trace
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []
    hover_text = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        node_data = G.nodes[node]
        node_text.append(node_data['label'])
        node_color.append(node_data['color'])
        node_size.append(20 + node_data['connections'] * 2)

        quality_icon = QUALITY_INDICATORS.get(node_data['quality'], '⚫')
        hover = f"<b>{node_data['fqdn']}</b><br>"
        hover += f"Type: {node_data['type']}<br>"
        hover += f"App Code: {node_data['app_code']}<br>"
        hover += f"Location: {node_data['location']}<br>"
        hover += f"Quality: {quality_icon}<br>"
        hover += f"Connections: {node_data['connections']}"
        hover_text.append(hover)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        text=node_text, textposition='top center',
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(color='#1565C0', width=2)
        ),
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=hover_text
    )

    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
    )

    return fig, G

# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def prepare_display_dataframe(df, show_audit=False):
    """Prepare dataframe for display."""
    display_df = df.copy()

    # Add quality indicators
    if 'record_quality_grade' in display_df.columns:
        display_df['quality'] = display_df['record_quality_grade'].map(QUALITY_INDICATORS).fillna('⚫')

    # Remove audit columns if not needed
    if not show_audit:
        audit_cols = ['created_at', 'created_by', 'updated_at', 'updated_by']
        display_df = display_df.drop(columns=[col for col in audit_cols if col in display_df.columns], errors='ignore')

    # Remove internal ID columns for cleaner display
    id_cols = ['component_id', 'component_type_id', 'component_subtype_id',
               'environment_id', 'physical_location_id', 'ops_status_id',
               'abstraction_level_id', 'protocol_id', 'relationship_id',
               'relationship_type_id', 'related_component_id']
    display_df = display_df.drop(columns=[col for col in id_cols if col in display_df.columns], errors='ignore')

    return display_df

def export_graph_json(G, components_df):
    """Export graph data as JSON."""
    nodes = []
    edges = []

    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        nodes.append({
            'id': int(node_id),
            'label': node_data['label'],
            'fqdn': node_data['fqdn'],
            'type': node_data['type'],
            'app_code': node_data['app_code'],
            'location': node_data['location'],
            'quality': node_data['quality'],
            'connections': int(node_data['connections'])
        })

    for edge in G.edges(data=True):
        edges.append({
            'source': int(edge[0]),
            'target': int(edge[1]),
            'relationship': edge[2].get('relationship', 'unknown')
        })

    return json.dumps({'nodes': nodes, 'edges': edges}, indent=2)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize database
    db = init_database()
    if not db:
        st.stop()

    # Load data
    with st.spinner("Loading data..."):
        components_df = load_components(db)
        relationships_df = load_relationships(db)

    # ========================================================================
    # SIDEBAR NAVIGATION (NOT TOP TABS!)
    # ========================================================================

    with st.sidebar:
        st.markdown("# 🏦 BAIS")
        # Removed separator for cleaner look

        # Navigation radio buttons in sidebar
        page = st.radio(
            "NAVIGATION",
            ["EXPLORER", "DASHBOARD", "NETWORK GRAPH", "COMPONENTS", "RELATIONSHIPS", "ERD", "ABOUT"],
            key="navigation_radio"
        )

        # Removed separator for cleaner look
        st.markdown("### SYSTEM INFO")
        st.info(f"📊 Schema: DEMO\n🔢 Components: {len(components_df)}\n🔗 Relationships: {len(relationships_df)}")

    # ========================================================================
    # MAIN PAGE AREA - FILTERS AT TOP (NOT IN SIDEBAR!)
    # ========================================================================

    # Main title
    st.markdown("# 🏦 BANK APPLICATION INVENTORY SYSTEM")

    # Create filter section at top of main page
    st.markdown("## FILTERS")

    # Create columns for filter layout
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        search_term = st.text_input(
            "SEARCH",
            placeholder="Enter search term...",
            key="search_input"
        )

    with filter_col2:
        env_options = sorted([e for e in components_df['environment'].dropna().unique() if e])
        env_filter = st.multiselect(
            "ENVIRONMENTS",
            options=env_options,
            default=[],
            key="env_filter"
        )

    with filter_col3:
        status_options = sorted([s for s in components_df['ops_status'].dropna().unique() if s])
        status_filter = st.multiselect(
            "OPERATIONAL STATUS",
            options=status_options,
            default=[],
            key="status_filter"
        )

    with filter_col4:
        type_options = sorted([t for t in components_df['component_type'].dropna().unique() if t])
        type_filter = st.multiselect(
            "COMPONENT TYPES",
            options=type_options,
            default=[],
            key="type_filter"
        )

    # Second row of filters
    filter2_col1, filter2_col2, filter2_col3, filter2_col4 = st.columns(4)

    with filter2_col1:
        show_audit = st.checkbox(
            "SHOW AUDIT COLUMNS",
            value=False,
            key="audit_checkbox"
        )

    with filter2_col2:
        graph_layout = st.radio(
            "GRAPH LAYOUT",
            options=["CIRCULAR", "FORCE-DIRECTED", "HIERARCHICAL"],
            index=0,
            key="graph_layout_radio",
            horizontal=True
        )

    st.markdown("---")

    # Apply filters to data
    filtered_components, filtered_relationships = apply_filters(
        components_df, relationships_df,
        search_term, env_filter, status_filter, type_filter
    )

    # ========================================================================
    # PAGE CONTENT BASED ON NAVIGATION
    # ========================================================================

    if page == "EXPLORER":
        # ====================================================================
        # EXPLORER PAGE - THREE VERTICALLY STACKED SYNCHRONIZED VIEWS
        # ====================================================================

        st.markdown("## INFRASTRUCTURE EXPLORER")
        st.info("🔍 ALL THREE VIEWS BELOW ARE SYNCHRONIZED - FILTERS APPLY TO ALL SIMULTANEOUSLY")

        # SECTION 1: COMPONENTS TABLE
        st.markdown("### 📊 COMPONENTS")
        display_components = prepare_display_dataframe(filtered_components, show_audit)
        st.dataframe(
            display_components,
            height=300,
            width='stretch',
            hide_index=True,
            key="explorer_components_df"
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            csv = display_components.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv,
                file_name=f"components_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="explorer_components_download"
            )

        # Removed separator for cleaner look

        # SECTION 2: RELATIONSHIPS TABLE
        st.markdown("### 🔗 RELATIONSHIPS")
        display_relationships = prepare_display_dataframe(filtered_relationships, show_audit)

        # Reorder columns for better readability
        if len(display_relationships) > 0:
            col_order = ['component_1', 'component_1_type', 'relationship_type', 'component_2', 'component_2_type']
            other_cols = [c for c in display_relationships.columns if c not in col_order]
            display_relationships = display_relationships[col_order + other_cols]

        st.dataframe(
            display_relationships,
            height=300,
            width='stretch',
            hide_index=True,
            key="explorer_relationships_df"
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            csv = display_relationships.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv,
                file_name=f"relationships_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="explorer_relationships_download"
            )

        # Removed separator for cleaner look

        # SECTION 3: NETWORK GRAPH
        st.markdown("### 🌐 NETWORK VISUALIZATION")

        if len(filtered_components) > 0:
            fig, G = create_network_graph(filtered_components, filtered_relationships, graph_layout)
            fig.update_layout(height=600)
            st.plotly_chart(fig, key="explorer_network_graph")

            # Graph stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("NODES", len(G.nodes()))
            with col2:
                st.metric("EDGES", len(G.edges()))
            with col3:
                avg_degree = sum(dict(G.degree()).values()) / len(G.nodes()) if len(G.nodes()) > 0 else 0
                st.metric("AVG DEGREE", f"{avg_degree:.2f}")

            # Export button
            col1, col2 = st.columns([1, 5])
            with col1:
                graph_json = export_graph_json(G, filtered_components)
                st.download_button(
                    label="📥 JSON",
                    data=graph_json,
                    file_name=f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="explorer_graph_download"
                )
        else:
            st.warning("No components to display with current filters")

    elif page == "DASHBOARD":
        # ====================================================================
        # DASHBOARD PAGE
        # ====================================================================

        st.markdown("## ANALYTICS DASHBOARD")

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("TOTAL COMPONENTS", len(filtered_components))

        with col2:
            st.metric("TOTAL RELATIONSHIPS", len(filtered_relationships))

        with col3:
            prod_count = len(filtered_components[filtered_components['environment'] == 'PROD']) if 'PROD' in filtered_components['environment'].values else 0
            st.metric("PRODUCTION COMPONENTS", prod_count)

        with col4:
            green_count = len(filtered_components[filtered_components['record_quality_grade'] == '_PT_GREEN_RECORD_'])
            st.metric("HIGH QUALITY RECORDS", green_count)

        # Removed separator for cleaner look

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### COMPONENTS BY TYPE")
            if len(filtered_components) > 0:
                type_counts = filtered_components['component_type'].value_counts()
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    color_discrete_map=COMPONENT_COLORS,
                    hole=0.4
                )
                # Add borders to pie slices
                fig.update_traces(
                    marker=dict(line=dict(color='#1565C0', width=2))
                )
                fig.update_layout(
                    height=400,
                    paper_bgcolor='white',
                    plot_bgcolor='white',
                    font=dict(color='#0D47A1')
                )
                st.plotly_chart(fig, key="dashboard_pie_chart")
            else:
                st.info("No data to display")

        with col2:
            st.markdown("### COMPONENTS BY ENVIRONMENT")
            if len(filtered_components) > 0:
                env_counts = filtered_components['environment'].value_counts()
                fig = px.bar(
                    x=env_counts.index,
                    y=env_counts.values,
                    color=env_counts.index,
                    labels={'x': 'ENVIRONMENT', 'y': 'COUNT'},
                    color_discrete_sequence=['#1565C0', '#2196F3', '#64B5F6', '#90CAF9']
                )
                # Add borders to bars
                fig.update_traces(
                    marker=dict(line=dict(color='#0D47A1', width=2))
                )
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    paper_bgcolor='white',
                    plot_bgcolor='white',
                    font=dict(color='#0D47A1'),
                    xaxis=dict(showgrid=True, gridcolor='#E3F2FD'),
                    yaxis=dict(showgrid=True, gridcolor='#E3F2FD')
                )
                st.plotly_chart(fig, key="dashboard_bar_chart")
            else:
                st.info("No data to display")

        # Quality distribution
        st.markdown("### DATA QUALITY DISTRIBUTION")
        if len(filtered_components) > 0:
            quality_counts = filtered_components['record_quality_grade'].value_counts()
            quality_df = pd.DataFrame({
                'Quality': quality_counts.index.map(lambda x: QUALITY_INDICATORS.get(x, '⚫') + ' ' + x),
                'Count': quality_counts.values
            })
            fig = px.bar(
                quality_df,
                x='Quality',
                y='Count',
                color='Quality',
                color_discrete_map={
                    '🟢 _PT_GREEN_RECORD_': '#4CAF50',
                    '🟡 _PT_YELLOW_RECORD_': '#FFC107',
                    '🔴 _PT_RED_RECORD_': '#F44336'
                }
            )
            # Add borders to bars
            fig.update_traces(
                marker=dict(line=dict(color='#0D47A1', width=2))
            )
            fig.update_layout(
                height=300,
                showlegend=False,
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(color='#0D47A1'),
                xaxis=dict(showgrid=True, gridcolor='#E3F2FD'),
                yaxis=dict(showgrid=True, gridcolor='#E3F2FD')
            )
            st.plotly_chart(fig, key="dashboard_quality_chart")
        else:
            st.info("No data to display")

    elif page == "NETWORK GRAPH":
        # ====================================================================
        # NETWORK GRAPH PAGE (DEDICATED)
        # ====================================================================

        st.markdown("## NETWORK GRAPH VISUALIZATION")

        if len(filtered_components) > 0:
            fig, G = create_network_graph(filtered_components, filtered_relationships, graph_layout)
            fig.update_layout(height=800)
            st.plotly_chart(fig, key="network_main_graph")

            # Graph statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("NODES", len(G.nodes()))
            with col2:
                st.metric("EDGES", len(G.edges()))
            with col3:
                avg_degree = sum(dict(G.degree()).values()) / len(G.nodes()) if len(G.nodes()) > 0 else 0
                st.metric("AVERAGE DEGREE", f"{avg_degree:.2f}")

            # Export button
            graph_json = export_graph_json(G, filtered_components)
            st.download_button(
                label="📥 JSON",
                data=graph_json,
                file_name=f"network_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="network_graph_download"
            )
        else:
            st.warning("No components to display with current filters")

    elif page == "COMPONENTS":
        # ====================================================================
        # COMPONENTS PAGE
        # ====================================================================

        st.markdown("## COMPONENTS DATA TABLE")

        display_components = prepare_display_dataframe(filtered_components, show_audit)
        st.dataframe(
            display_components,
            height=600,
            width='stretch',
            hide_index=True,
            key="components_main_table"
        )

        # Statistics
        st.markdown("### STATISTICS")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("TOTAL COMPONENTS", len(filtered_components))
        with col2:
            st.metric("UNIQUE TYPES", filtered_components['component_type'].nunique())
        with col3:
            st.metric("UNIQUE ENVIRONMENTS", filtered_components['environment'].nunique())
        with col4:
            st.metric("UNIQUE LOCATIONS", filtered_components['physical_location'].nunique())

        # Export
        csv = display_components.to_csv(index=False)
        st.download_button(
            label="📥 CSV",
            data=csv,
            file_name=f"all_components_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="components_page_download"
        )

    elif page == "RELATIONSHIPS":
        # ====================================================================
        # RELATIONSHIPS PAGE
        # ====================================================================

        st.markdown("## RELATIONSHIPS DATA TABLE")

        display_relationships = prepare_display_dataframe(filtered_relationships, show_audit)

        # Reorder columns
        if len(display_relationships) > 0:
            col_order = ['component_1', 'component_1_type', 'relationship_type', 'component_2', 'component_2_type']
            other_cols = [c for c in display_relationships.columns if c not in col_order]
            display_relationships = display_relationships[col_order + other_cols]

        st.dataframe(
            display_relationships,
            height=600,
            width='stretch',
            hide_index=True,
            key="relationships_main_table"
        )

        # Statistics
        st.markdown("### STATISTICS")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("TOTAL RELATIONSHIPS", len(filtered_relationships))
        with col2:
            if len(filtered_relationships) > 0:
                st.metric("UNIQUE TYPES", filtered_relationships['relationship_type'].nunique())
            else:
                st.metric("UNIQUE TYPES", 0)
        with col3:
            if len(filtered_relationships) > 0:
                most_common = filtered_relationships['relationship_type'].value_counts().index[0]
                st.metric("MOST COMMON TYPE", most_common)
            else:
                st.metric("MOST COMMON TYPE", "N/A")

        # Export
        csv = display_relationships.to_csv(index=False)
        st.download_button(
            label="📥 CSV",
            data=csv,
            file_name=f"all_relationships_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="relationships_page_download"
        )

    elif page == "ERD":
        # ====================================================================
        # ERD PAGE
        # ====================================================================

        st.markdown("## ENTITY RELATIONSHIP DIAGRAM")

        st.info("📊 The ERD shows the database schema structure for the BAIS system")

        # Visual ERD Generation Section
        if HAS_ERALCHEMY:
            st.divider()
            st.markdown("### 📈 VISUAL DATABASE DIAGRAM")

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write("Generate a visual Entity Relationship Diagram for the demo schema")

            with col2:
                if st.button("🔄 GENERATE ERD", key="generate_erd_btn", use_container_width=True):
                    with st.spinner("Generating ERD diagram..."):
                        try:
                            # Get database URL and generate ERD
                            db_url = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL')
                            if db_url:
                                # Add schema to URL
                                schema = 'demo'
                                if '?' in db_url:
                                    schema_url = f"{db_url}&options=-csearch_path={schema}"
                                else:
                                    schema_url = f"{db_url}?options=-csearch_path={schema}"

                                # Generate ERD to temp file
                                temp_dir = tempfile.gettempdir()
                                erd_file = os.path.join(temp_dir, f"bais_erd_{schema}_{os.getpid()}.png")

                                # Generate ERD
                                render_er(schema_url, erd_file)

                                if os.path.exists(erd_file):
                                    with open(erd_file, 'rb') as f:
                                        img_data = f.read()
                                    os.remove(erd_file)  # Clean up temp file
                                    st.session_state['erd_image'] = img_data
                                    st.success("✅ ERD generated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to generate ERD file")
                            else:
                                st.error("Database connection not configured")
                        except Exception as e:
                            st.error(f"❌ Error generating ERD: {str(e)}")

            with col3:
                if 'erd_image' in st.session_state:
                    st.download_button(
                        label="📥 DOWNLOAD PNG",
                        data=st.session_state['erd_image'],
                        file_name=f"bais_erd_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        mime="image/png",
                        key="download_erd_btn",
                        use_container_width=True
                    )

            # Display the ERD if it exists
            if 'erd_image' in st.session_state:
                st.image(
                    st.session_state['erd_image'],
                    caption="BAIS Database ERD - Demo Schema",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ ERD generation not available. Install eralchemy2 and graphviz to enable visual diagrams.")
            st.code("pip install eralchemy2 pygraphviz", language="bash")

        st.divider()
        st.markdown("### CURRENT SCHEMA: DEMO")

        st.markdown("""
        The BAIS database consists of the following main tables:

        #### BUSINESS TABLES
        - **biz_components** - Main components table with network identity
        - **biz_component_relationships** - Relationships between components

        #### REFERENCE TABLES
        - **component_types** - Component type definitions (application, persistence, networking)
        - **component_subtypes** - Component subtype definitions
        - **component_environments** - Environment definitions (DEV, TEST, PROD)
        - **component_physical_locations** - Physical datacenter locations
        - **component_ops_statuses** - Operational status definitions
        - **component_abstraction_levels** - Abstraction levels (VM, container, etc.)
        - **component_protocols** - Network protocol definitions
        - **component_relationship_types** - Relationship type definitions

        #### KEY RELATIONSHIPS
        - Components have foreign keys to all reference tables
        - Relationships link two components with a relationship type
        - All tables include audit columns (created_at, created_by, updated_at, updated_by)
        """)

    elif page == "ABOUT":
        # ====================================================================
        # ABOUT PAGE
        # ====================================================================

        st.markdown("## ABOUT BAIS")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### SYSTEM INFORMATION

            - **Version:** 2.0.0
            - **Schema:** DEMO
            - **Database:** PostgreSQL
            - **Framework:** Streamlit

            ### FEATURES

            ✅ **Multi-View Explorer** - Three synchronized views
            ✅ **Interactive Network Visualization**
            ✅ **Real-time Filtering** - All views update together
            ✅ **CSV & JSON Export**
            ✅ **Quality Indicators**
            ✅ **Audit Trail Support**
            """)

        with col2:
            st.markdown("""
            ### DATA QUALITY INDICATORS

            - 🟢 **GREEN** - Complete, validated records
            - 🟡 **YELLOW** - Records pending validation
            - 🔴 **RED** - Records with issues or missing data

            ### SPECIAL VALUES

            - **_PT_PENDING_** - Data discovery pending
            - **_PT_NO_DATA_FOUND_** - No data available

            ### COMPONENT TYPES

            - 🟢 **application** - Core software applications
            - 🔵 **polyglot_persistence** - Various database technologies
            - 🟠 **block_level_persistence** - Storage systems
            - 🔴 **networking** - Network infrastructure
            """)

if __name__ == "__main__":
    main()
