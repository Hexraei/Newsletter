"""
Excel-based tracking system for scraper testing and debugging.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import os


class ExcelTracker:
    """Track scraper tests and results in Excel."""
    
    def __init__(self, filepath: str = "data/scraper_tests.xlsx"):
        self.filepath = filepath
        self.sheet_results = "Test Results"
        self.sheet_sources = "Source Status"
        self.sheet_items = "Scraped Items"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Initialize Excel file if it doesn't exist
        if not os.path.exists(filepath):
            self._initialize_excel()
    
    def _initialize_excel(self):
        """Create initial Excel structure."""
        # Source status sheet
        sources_df = pd.DataFrame(columns=[
            'source_name',
            'source_type',
            'method',
            'status',
            'last_tested',
            'items_count',
            'error_message',
            'notes'
        ])
        
        # Test results sheet
        results_df = pd.DataFrame(columns=[
            'timestamp',
            'source_name',
            'test_type',
            'status',
            'items_found',
            'time_taken_sec',
            'error_message'
        ])
        
        # Scraped items sheet
        items_df = pd.DataFrame(columns=[
            'source',
            'source_type',
            'title',
            'url',
            'author',
            'published_at',
            'scraped_at',
            'engagement',
            'content_hash'
        ])
        
        with pd.ExcelWriter(self.filepath, engine='openpyxl') as writer:
            sources_df.to_excel(writer, sheet_name=self.sheet_sources, index=False)
            results_df.to_excel(writer, sheet_name=self.sheet_results, index=False)
            items_df.to_excel(writer, sheet_name=self.sheet_items, index=False)
    
    def add_source_status(self, 
                          source_name: str,
                          source_type: str,
                          method: str,
                          status: str,
                          items_count: int = 0,
                          error_message: str = "",
                          notes: str = ""):
        """Update source status."""
        try:
            df = pd.read_excel(self.filepath, sheet_name=self.sheet_sources)
            
            # Remove existing entry for this source
            df = df[df['source_name'] != source_name]
            
            # Add new entry
            new_row = pd.DataFrame([{
                'source_name': source_name,
                'source_type': source_type,
                'method': method,
                'status': status,
                'last_tested': datetime.now(),
                'items_count': items_count,
                'error_message': error_message,
                'notes': notes
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            
            with pd.ExcelWriter(self.filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=self.sheet_sources, index=False)
                
        except Exception as e:
            print(f"Error updating source status: {e}")
    
    def add_test_result(self,
                       source_name: str,
                       test_type: str,
                       status: str,
                       items_found: int = 0,
                       time_taken_sec: float = 0.0,
                       error_message: str = ""):
        """Add test result."""
        try:
            df = pd.read_excel(self.filepath, sheet_name=self.sheet_results)
            
            new_row = pd.DataFrame([{
                'timestamp': datetime.now(),
                'source_name': source_name,
                'test_type': test_type,
                'status': status,
                'items_found': items_found,
                'time_taken_sec': time_taken_sec,
                'error_message': error_message
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            
            with pd.ExcelWriter(self.filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=self.sheet_results, index=False)
                
        except Exception as e:
            print(f"Error adding test result: {e}")
    
    def add_scraped_items(self, items: List[Dict[str, Any]]):
        """Add scraped items to Excel."""
        if not items:
            return
            
        try:
            df = pd.read_excel(self.filepath, sheet_name=self.sheet_items)
            
            new_rows = pd.DataFrame(items)
            df = pd.concat([df, new_rows], ignore_index=True)
            
            # Remove duplicates based on content_hash
            if 'content_hash' in df.columns:
                df = df.drop_duplicates(subset=['content_hash'], keep='last')
            
            with pd.ExcelWriter(self.filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=self.sheet_items, index=False)
                
        except Exception as e:
            print(f"Error adding scraped items: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tests."""
        try:
            sources_df = pd.read_excel(self.filepath, sheet_name=self.sheet_sources)
            
            total_sources = len(sources_df)
            working = len(sources_df[sources_df['status'] == 'working'])
            failed = len(sources_df[sources_df['status'] == 'failed'])
            skipped = len(sources_df[sources_df['status'] == 'skipped'])
            
            return {
                'total_sources': total_sources,
                'working': working,
                'failed': failed,
                'skipped': skipped,
                'success_rate': f"{(working/max(total_sources, 1))*100:.1f}%"
            }
        except Exception as e:
            return {'error': str(e)}
    
    def print_summary(self):
        """Print summary to console."""
        summary = self.get_summary()
        print("\n" + "="*60)
        print("SCRAPER TEST SUMMARY")
        print("="*60)
        for key, value in summary.items():
            print(f"{key}: {value}")
        print("="*60 + "\n")
