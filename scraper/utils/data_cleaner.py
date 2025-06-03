"""
Data cleaning utilities for property data.
"""

import pandas as pd
import numpy as np
import re
import logging
from datetime import datetime
from typing import Dict, List, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCleaner:
    """Class to handle all data cleaning operations for property data."""
    
    @staticmethod
    def standardize_property_type(prop_type: str) -> str:
        """Standardize property type classification."""
        if pd.isna(prop_type) or prop_type is None:
            return 'Unknown'
        else:
            return prop_type

    @staticmethod
    def extract_numeric_value(value: str) -> float:
        """Extract numeric value from string."""
        if pd.isna(value) or value is None or value == '- sqft':
            return np.nan
        match = re.search(r'([\d,]+)', str(value))
        return float(match.group(1).replace(',', '')) if match else np.nan
    
    @staticmethod
    def extract_count(value: str) -> int:
        """Extract numeric count from string (e.g., for bedrooms/bathrooms)."""
        if pd.isna(value) or value is None:
            return np.nan
        match = re.search(r'(\d+)', str(value))
        return int(match.group(1)) if match else np.nan
    
    @staticmethod
    def extract_price_info(price_str: str) -> pd.Series:
        """
        Extract main price and price per square foot from price string.
        Example inputs:
        - 'RM341,000(RM 193 Psf)'
        - 'RM1,000,000(RM 380 Psf)'
        - 'RM550,000'
        Returns tuple of (main_price, price_per_sqft)
        """
        if pd.isna(price_str) or price_str is None:
            return pd.Series([np.nan, np.nan])
        
        price_str = str(price_str)
        
        # Extract main price (handle numbers with commas)
        main_price = np.nan
        price_match = re.search(r'RM([\d,]+)', price_str)
        if price_match:
            try:
                main_price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                main_price = np.nan
        
        # Extract price per sqft (look for pattern after main price)
        price_per_sqft = np.nan
        psf_match = re.search(r'\(RM\s*([\d,.]+)\s*(?:Psf|PSF|per\s*sqft)?\)', price_str)
        if psf_match:
            try:
                price_per_sqft = float(psf_match.group(1).replace(',', ''))
            except ValueError:
                price_per_sqft = np.nan
            
        return pd.Series([main_price, price_per_sqft])
    
    def clean_data(self, data: List[Dict]) -> pd.DataFrame:
        """Clean and transform property data into a structured DataFrame."""
        from datetime import datetime
        
        # Convert list of dictionaries to DataFrame
        if not data:
            logger.warning("Empty data provided to clean_data")
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # Create expanded_df to store the cleaned data
        expanded_df = pd.DataFrame()
        
        # Define required columns with default values
        required_columns = {
            'propertyType': 'Unknown',
            'floorSize': 0,
            'numberOfBedrooms': 0,
            'numberOfBathrooms': 0,
            'price': 'RM0',
            'property_desc': '',
            'address': '',
            'agent': '',
            'agent_desc': '',
            'link': '',
            'lotType': 'Unknown'
        }
        
        # Add missing columns with default values
        for col, default in required_columns.items():
            if col not in df.columns:
                logger.warning(f"Column '{col}' not found, adding with default value")
                df[col] = default
        
        # Clean and standardize the data
        expanded_df['property_desc'] = df['property_desc'].fillna('')
        expanded_df['address'] = df['address'].fillna('')
        expanded_df['property_type'] = df['propertyType'].apply(self.standardize_property_type)
        
        # Handle floor size standardization (convert to sqft if needed)
        def standardize_floor_size(size):
            if isinstance(size, (int, float)):
                return f"{size:,.0f} sqft"
            elif isinstance(size, str):
                # Remove commas and convert to float if possible
                try:
                    return f"{float(size.replace(',', '')):,.0f} sqft"
                except ValueError:
                    return size
            return "0 sqft"
        
        expanded_df['floor_size_sqft'] = df['floorSize'].apply(standardize_floor_size)
        
        # Clean numeric values
        expanded_df['num_bedrooms'] = df['numberOfBedrooms'].apply(self.extract_count)
        expanded_df['num_bathrooms'] = df['numberOfBathrooms'].apply(self.extract_count)
        
        # Extract price information
        expanded_df['asked_price'] = df['price'].apply(lambda x: self.extract_price_info(x)[0])
        expanded_df['price_per_sqft'] = df['price'].apply(lambda x: self.extract_price_info(x)[1])
        
        # Add agent information
        expanded_df['agent'] = df['agent'].fillna('')
        expanded_df['agent_desc'] = df['agent_desc'].fillna('')
        expanded_df['link'] = df['link'].fillna('')
        
        # Add lot type if available
        expanded_df['lot_type'] = df['lotType'].fillna('Unknown')
        
        # Add crawled_at from input data
        expanded_df['crawled_at'] = df['crawled_at'].fillna(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Select and reorder final columns
        columns_to_select = [
            'property_desc',
            'address',
            'property_type',
            'asked_price',
            'price_per_sqft',
            'floor_size_sqft',
            'num_bedrooms',
            'num_bathrooms',
            'agent',
            'agent_desc',
            'link',
            'lot_type',
            'crawled_at'
        ]
        
        # Ensure all columns exist
        for col in columns_to_select:
            if col not in expanded_df.columns:
                logger.warning(f"Output column '{col}' not found, adding empty column")
                expanded_df[col] = ''
        
        cleaned_df = expanded_df[columns_to_select]
        return cleaned_df 