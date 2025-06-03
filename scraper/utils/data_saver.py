"""
Data saving utilities for property data.
"""

import os
import json
import logging
from typing import Dict, List
import pandas as pd
from utils.data_cleaner import DataCleaner

logger = logging.getLogger(__name__)

class DataSaver:
    """Class to handle saving data in different formats."""
    
    def __init__(self, data_cleaner: DataCleaner):
        """Initialize DataSaver with a DataCleaner instance."""
        self.data_cleaner = data_cleaner
    
    def save_json(self, data: List[Dict], filename: str) -> None:
        """
        Save data to JSON file by appending to existing data.
        
        Args:
            data: List of property dictionaries to save
            filename: Output JSON file path
        """
        try:
            # Read existing data if file exists
            existing_data = []
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                try:
                    with open(filename, 'r') as f:
                        existing_data = json.load(f)
                        if not isinstance(existing_data, list):
                            existing_data = []
                            logger.warning(f"Existing data in {filename} is not a list. Creating new list.")
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse existing JSON in {filename}. Creating new list.")
            
            # Combine existing data with new data
            combined_data = existing_data + data
            
            # Write combined data back to file
            with open(filename, 'w') as f:
                json.dump(combined_data, f, indent=2)
                
            logger.info(f"Data successfully saved to {filename}")
            logger.info(f"Total JSON records: {len(combined_data)}")
            
        except Exception as e:
            logger.error(f"Error saving JSON data: {e}")
            raise
    
    def save_excel(self, data: List[Dict], filename: str) -> None:
        """
        Save cleaned data to Excel file, handling appending if file exists.
        
        Args:
            data: List of property dictionaries to save
            filename: Output Excel file path (should end with .xlsx)
        """
        try:
            # Clean the data
            cleaned_df = self.data_cleaner.clean_data(data)
            
            # If file exists, read existing data and append new data
            if os.path.exists(filename):
                try:
                    existing_df = pd.read_excel(filename, engine='openpyxl')
                    combined_df = pd.concat([existing_df, cleaned_df], ignore_index=True)
                except Exception as e:
                    logger.warning(f"Could not read existing Excel file: {e}. Creating new file.")
                    combined_df = cleaned_df
            else:
                combined_df = cleaned_df
            
            # Save to Excel with optimized settings
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                combined_df.to_excel(writer, index=False, sheet_name='Properties')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Properties']
                for idx, col in enumerate(combined_df.columns):
                    max_length = max(
                        combined_df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    # Add a little extra space
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            logger.info(f"Data successfully saved to {filename}")
            logger.info(f"Total Excel records: {len(combined_df)}")
            
        except Exception as e:
            logger.error(f"Error saving Excel data: {e}")
            raise
    
    def save_all(self, data: List[Dict], base_filename: str) -> None:
        """
        Save data to both JSON and Excel formats.
        
        Args:
            data: List of property dictionaries to save
            base_filename: Base filename without extension
        """
        json_filename = f"{base_filename}.json"
        excel_filename = f"{base_filename}.xlsx"
        
        try:
            self.save_json(data, json_filename)
            self.save_excel(data, excel_filename)
            logger.info("Successfully saved data in both JSON and Excel formats")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            raise 