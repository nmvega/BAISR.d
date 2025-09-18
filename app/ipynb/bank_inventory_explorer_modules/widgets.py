"""
UI component factories and state management.
"""

import logging
import ipywidgets as widgets
from IPython.display import HTML

logger = logging.getLogger(__name__)


class WidgetManager:
    """
    Manages widget state and references.
    """
    
    def __init__(self):
        """Initialize widget manager."""
        self.widgets = {}
        logger.debug("WidgetManager initialized")
    
    def register(self, name, widget):
        """Register a widget."""
        self.widgets[name] = widget
        logger.debug(f"Registered widget: {name}")
    
    def get(self, name):
        """Get a registered widget."""
        return self.widgets.get(name)
    
    def clear(self):
        """Clear all widgets."""
        self.widgets = {}
        logger.debug("Cleared all widgets")


def create_schema_selector(initial_value='demo', on_change=None):
    """
    Create schema selector dropdown.
    
    Args:
        initial_value (str): Initial schema value
        on_change (function): Callback for value changes
        
    Returns:
        widgets.Dropdown: Schema selector widget
    """
    selector = widgets.Dropdown(
        options=[('Demo Data', 'demo'), ('Live Production', 'public')],
        value=initial_value,
        description='Database Mode:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='300px')
    )
    
    if on_change:
        selector.observe(on_change, names='value')
    
    logger.debug(f"Created schema selector with initial value: {initial_value}")
    return selector


def create_status_indicator(schema):
    """
    Create status indicator for current schema.
    
    Args:
        schema (str): Current schema name
        
    Returns:
        widgets.HTML: Status indicator widget
    """
    if schema == 'public':
        html = '''
        <div style="background-color: #ffebee; color: #c62828; padding: 10px; 
                    border-radius: 5px; border-left: 4px solid #f44336;">
            <strong>🔴 LIVE MODE</strong> - Production Data
        </div>
        '''
    else:
        html = '''
        <div style="background-color: #e3f2fd; color: #1565c0; padding: 10px; 
                    border-radius: 5px; border-left: 4px solid #2196f3;">
            <strong>🟦 DEMO MODE</strong> - Sample Data
        </div>
        '''
    
    logger.debug(f"Created status indicator for schema: {schema}")
    return widgets.HTML(value=html)


def create_refresh_button(on_click, label='🔄 Refresh'):
    """
    Create refresh button.
    
    Args:
        on_click (function): Click handler
        label (str): Button label
        
    Returns:
        widgets.Button: Refresh button
    """
    button = widgets.Button(
        description=label,
        button_style='info',
        layout=widgets.Layout(width='150px')
    )
    
    if on_click:
        button.on_click(on_click)
    
    logger.debug(f"Created refresh button: {label}")
    return button


def create_export_button(export_type):
    """
    Create export button.
    
    Args:
        export_type (str): Type of export (json, png, csv)
        
    Returns:
        widgets.Button: Export button
    """
    buttons = {
        'json': ('💾 Export JSON', 'warning'),
        'png': ('📷 Export PNG', 'success'),
        'csv': ('📥 Export CSV', 'success')
    }
    
    label, style = buttons.get(export_type, ('Export', 'info'))
    
    button = widgets.Button(
        description=label,
        button_style=style,
        layout=widgets.Layout(width='150px')
    )
    
    logger.debug(f"Created export button: {export_type}")
    return button


def create_layout_selector():
    """
    Create layout selector dropdown.
    
    Returns:
        widgets.Dropdown: Layout selector
    """
    selector = widgets.Dropdown(
        options=['Force-Directed', 'Hierarchical', 'Circular', 'Grid'],
        value='Circular',
        description='Layout:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='200px')
    )
    
    logger.debug(f"Created layout selector: {selector.value}")
    return selector


def create_sizing_selector():
    """
    Create node sizing selector dropdown.
    
    Returns:
        widgets.Dropdown: Sizing selector
    """
    selector = widgets.Dropdown(
        options=['Combined Count', 'Hierarchical Only', 'Dependencies Only', 
                'Peer Relations Only', 'Uniform Size'],
        value='Combined Count',
        description='Node Size:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='250px')
    )
    
    logger.debug(f"Created sizing selector: {selector.value}")
    return selector


def create_search_box():
    """
    Create search input box.
    
    Returns:
        widgets.Text: Search box
    """
    search = widgets.Text(
        placeholder='Search components...',
        description='Search:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='300px')
    )
    
    logger.debug("Created search box")
    return search


def create_filter_checkboxes():
    """
    Create relationship filter checkboxes with proper width for full labels.
    
    Returns:
        dict: Dictionary of checkbox widgets
    """
    checkboxes = {
        'hierarchical': widgets.Checkbox(
            value=True,
            description='Hierarchical',
            layout=widgets.Layout(width='auto'),  # Auto width for full label
            style={'description_width': 'initial'}  # Allow description to use its natural width
        ),
        'dependencies': widgets.Checkbox(
            value=True,
            description='Dependencies',
            layout=widgets.Layout(width='auto'),  # Auto width for full label
            style={'description_width': 'initial'}  # Allow description to use its natural width
        ),
        'peer': widgets.Checkbox(
            value=True,
            description='Peer Relations',
            layout=widgets.Layout(width='auto'),  # Auto width for full label
            style={'description_width': 'initial'}  # Allow description to use its natural width
        )
    }
    
    logger.debug("Created filter checkboxes")
    return checkboxes


def create_section_header(title, icon=''):
    """
    Create section header HTML.
    
    Args:
        title (str): Section title
        icon (str): Optional icon
        
    Returns:
        widgets.HTML: Section header
    """
    html = f'''
    <h3 style="color: #1565C0; border-bottom: 2px solid #1565C0; 
               padding-bottom: 5px; margin-top: 20px;">
        {icon} {title}
    </h3>
    '''
    
    return widgets.HTML(value=html)


def create_output_area(height='400px'):
    """
    Create output area widget with PROPER HEIGHT (BUG FIX!).
    
    Args:
        height (str): CSS height value
        
    Returns:
        widgets.Output: Output area
    """
    output = widgets.Output(
        layout=widgets.Layout(
            height=height,
            overflow='auto',
            border='1px solid #ddd',
            padding='10px'
        )
    )
    
    logger.debug(f"Created output area with height: {height}")
    return output


def create_tabbed_tables():
    """
    Create properly tabbed table container - 2 tabs for single-table schema.
    
    Returns:
        tuple: (tab_widget, components_output, relationships_output)
    """
    # Create output areas for each table
    components_output = widgets.Output()
    relationships_output = widgets.Output()
    
    # Create Tab widget with 2 tabs (removed redundant dependencies tab)
    tab = widgets.Tab()
    tab.children = [components_output, relationships_output]
    
    # Set tab titles
    for i, title in enumerate(['Components', 'Relationships']):
        tab.set_title(i, title)
    
    logger.debug("Created tabbed table container with 2 tabs")
    return tab, components_output, relationships_output


def create_graph_container():
    """
    Create graph container with PROPER HEIGHT (BUG FIX!).
    
    Returns:
        widgets.Output: Graph output area with 1200px height
    """
    output = widgets.Output(
        layout=widgets.Layout(
            height='1200px',  # FIX: Much taller container!
            width='100%',
            overflow='auto',
            border='2px solid #1565C0',
            border_radius='5px',
            padding='10px'
        )
    )
    
    logger.debug("Created graph container with 1200px height")
    return output


def create_control_panel():
    """
    Create control panel container.
    
    Returns:
        widgets.VBox: Control panel
    """
    return widgets.VBox(
        layout=widgets.Layout(
            padding='10px',
            border='1px solid #ddd',
            border_radius='5px'
        )
    )