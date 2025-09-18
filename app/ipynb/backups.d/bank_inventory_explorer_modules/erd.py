"""
Entity Relationship Diagram generation (CRITICAL MISSING FEATURE!).
"""

import os
import logging
import tempfile
import base64
from pathlib import Path
import ipywidgets as widgets
from IPython.display import Image, display, HTML

try:
    from eralchemy2 import render_er
    HAS_ERALCHEMY = True
except ImportError:
    HAS_ERALCHEMY = False
    logging.warning("eralchemy2 not installed. ERD generation disabled.")

logger = logging.getLogger(__name__)


class ERDGenerator:
    """
    Generate Entity Relationship Diagrams for database schema.
    This was COMPLETELY MISSING from the buggy v2 implementation!
    """
    
    def __init__(self, database_connection):
        """
        Initialize ERD generator.
        
        Args:
            database_connection: DatabaseConnection instance
        """
        self.db = database_connection
        self.temp_dir = tempfile.gettempdir()
        logger.debug(f"ERDGenerator initialized (eralchemy2: {HAS_ERALCHEMY})")
    
    def generate_erd(self, schema='demo', output_format='png'):
        """
        Generate ERD for the specified schema.
        
        Args:
            schema (str): Database schema to visualize
            output_format (str): Output format (png, pdf, svg)
            
        Returns:
            str: Path to generated ERD file or None if failed
        """
        if not HAS_ERALCHEMY:
            logger.error("eralchemy2 not available for ERD generation")
            return None
        
        try:
            # Get database URL
            db_url = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL')
            if not db_url:
                logger.error("POSTGRESQL_BAIS_DB_ADMIN_URL not found")
                return None
            
            # Add schema to URL
            if '?' in db_url:
                schema_url = f"{db_url}&options=-csearch_path={schema}"
            else:
                schema_url = f"{db_url}?options=-csearch_path={schema}"
            
            # Generate output filename
            output_file = os.path.join(
                self.temp_dir, 
                f"erd_{schema}_{os.getpid()}.{output_format}"
            )
            
            logger.info(f"Generating ERD for {schema} schema...")
            
            # Generate ERD
            render_er(schema_url, output_file)
            
            if os.path.exists(output_file):
                logger.info(f"✓ ERD generated: {output_file}")
                return output_file
            else:
                logger.error("ERD file not created")
                return None
                
        except Exception as e:
            logger.error(f"ERD generation failed: {e}")
            return None
    
    def display_erd(self, schema='demo'):
        """
        Generate and display ERD inline.
        
        Args:
            schema (str): Database schema to visualize
            
        Returns:
            Image or HTML widget
        """
        erd_path = self.generate_erd(schema, 'png')
        
        if erd_path and os.path.exists(erd_path):
            return Image(filename=erd_path)
        else:
            return widgets.HTML(
                value='<p style="color: red;">⚠️ ERD generation failed. '
                      'Make sure eralchemy2 is installed: pip install eralchemy2</p>'
            )
    
    def create_erd_download_link(self, schema='demo'):
        """
        Generate ERD and create download link.
        
        Args:
            schema (str): Database schema to visualize
            
        Returns:
            widgets.HTML: Download link or error message
        """
        erd_path = self.generate_erd(schema, 'png')
        
        if not erd_path or not os.path.exists(erd_path):
            return widgets.HTML(
                value='<p style="color: red;">ERD generation failed</p>'
            )
        
        try:
            # Read the image file
            with open(erd_path, 'rb') as f:
                img_data = f.read()
            
            # Encode to base64
            b64 = base64.b64encode(img_data).decode()
            
            # Create download link
            href = f'<a href="data:image/png;base64,{b64}" download="erd_{schema}.png">'
            href += f'📊 Download ERD ({schema} schema)</a>'
            
            # Clean up temp file
            try:
                os.remove(erd_path)
            except:
                pass
            
            return widgets.HTML(value=href)
            
        except Exception as e:
            logger.error(f"Failed to create download link: {e}")
            return widgets.HTML(
                value='<p style="color: red;">Failed to create download link</p>'
            )


def create_erd_section(database_connection):
    """
    Create complete ERD section with controls and display.
    
    Args:
        database_connection: DatabaseConnection instance
        
    Returns:
        widgets.VBox: ERD section widget
    """
    generator = ERDGenerator(database_connection)
    
    # Create output area
    output = widgets.Output(
        layout=widgets.Layout(
            height='600px',
            overflow='auto',
            border='1px solid #ddd',
            padding='10px'
        )
    )
    
    # Create controls
    schema_selector = widgets.Dropdown(
        options=[
            ('DEMO', 'demo'),
            ('LIVE', 'live'),
            ('LIVE_MASKED', 'live_masked')
        ],
        value='demo',
        description='Schema:',
        style={'description_width': 'initial'}
    )
    
    generate_button = widgets.Button(
        description='🔄 Generate ERD',
        button_style='primary',
        layout=widgets.Layout(width='150px')
    )
    
    download_area = widgets.Output()
    
    def on_generate_click(b):
        """Handle generate button click."""
        output.clear_output()
        download_area.clear_output()
        
        with output:
            display(widgets.HTML(
                value='<p>🔄 Generating ERD...</p>'
            ))
            
            # Generate and display ERD
            erd_display = generator.display_erd(schema_selector.value)
            output.clear_output()
            display(erd_display)
        
        with download_area:
            # Create download link
            download_link = generator.create_erd_download_link(schema_selector.value)
            display(download_link)
    
    generate_button.on_click(on_generate_click)
    
    # Check if eralchemy2 is available
    if not HAS_ERALCHEMY:
        warning = widgets.HTML(
            value='''
            <div style="background-color: #fff3cd; color: #856404; 
                        padding: 10px; border-radius: 5px; 
                        border-left: 4px solid #ffc107;">
                <strong>⚠️ Warning:</strong> eralchemy2 is not installed. 
                Install it with: <code>pip install eralchemy2</code>
            </div>
            '''
        )
    else:
        warning = widgets.HTML(value='')
    
    # Create layout
    controls = widgets.HBox([
        schema_selector,
        generate_button,
        download_area
    ])
    
    return widgets.VBox([
        widgets.HTML(
            value='<h3 style="color: #1565C0;">📊 Entity Relationship Diagram</h3>'
        ),
        warning,
        controls,
        output
    ])
