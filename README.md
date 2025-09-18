# Network Segmentation Application Inventory System

A Postgres and Python-based system for cataloging (in-scope) **components** (e.g., apps, databases, queues, etc.) and their **relationships** to support network segmentation initiatives.

## Overview

This system provides tools and utilities to systematically inventory the organizations's discovered **components** and their **relationships**. The platform uses **PostgreSQL** as its core data store to democratize discovered information and enable network segmentation analysis across teams.

## Key Features

### Database Management
- **Multi-schema PostgreSQL architecture**: 
  - `live` - Production inventory data
  - `demo` - Testing and demonstration data
  - `live_masked` - Anonymized replica for advanced LLM-driven analytics (future)
- **Structured data model** with `biz_components` (components) and `biz_component_relationships` (inter-application dependencies)
- **Database initialization and population tools**

### Data Inventorying
- **Spreadsheet ingestion tools** for structured data ingestion of `PowerBI` exports during discovery phases.
- **Row-level data validation and quality tracking**.

### Analysis & Demonstration
- **Jupyter notebook examples** showcasing data analysis capabilities
- **Sample applications** demonstrating practical use of the inventory data
- **Relationship mapping tools** to visualize application dependencies

## Database Schema

### Core Tables
- **`biz_components`**: Table to capture **components** with network details, datacenter locations, and metadata.
- **`biz_component_relationships`**: Table to capture **relationships** between components.

### Reference Tables
- Additional lookup tables for standardized categorization. Example: **`component_protocols`** (HTTP, HTTPS, SSH, database protocols, etc.).

## Various Use Cases

- **Network segmentation planning**: Understand intra-component relationships.
- **Risk assessment**: Identify critical component dependencies (e.g., **app01pri** and **app01sec** in the same datacenter)
- **Infrastructure mapping**: Catalog datacenter locations and network topology
- **Compliance reporting**: Generate inventory reports for audit purposes

## Technology Stack

- **Python 3.x** - Core development language
- **PostgreSQL** - Primary data store
- **Jupyter Notebooks** - Analysis and demonstration platform
- **Pandas/SQLAlchemy** - Data manipulation and database connectivity
- **Excel/CSV support** - Data import/export capabilities

## Getting Started

### Prerequisites
- Python 3.13+
- PostgreSQL 13+
- Required Python packages (see `requirements.txt`)

### Installation
```bash
git clone [repository-url]
cd network-segmentation-inventory
pip install -r requirements.txt
```application

### Database Setup
```bash
# Initialize database schemas
python scripts/init_database.py

# Load reference data
python scripts/load_reference_data.py
```

## Inaugural Project Structure (subject to change).

```
├── app/
│   ├── configs/           # YAML files for various Python modules.
│   ├── database/          # Database schema definition script.
│   ├── ipynb/             # Jupyter Notebook examples.
│   ├── scripts/           # Initialization and utility scripts.
│   ├── utils/             # Various utilities used by Python modules.
│   └── var/               # Directory for ephemeral files.
└── requirements.txt       # Collection of libraries and versions for the Python virtual environment.
```

## Future Capabilities

This interim tactical system is designed with open tools, data democratization and extensibility in mind, including **aspirational** accommodation of **business-oriented** users through natural-language database querying capabilities via **LLMs**.
