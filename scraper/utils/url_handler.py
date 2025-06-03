"""
URL handling utilities for property crawler.
"""

from urllib.parse import urljoin, urlparse

class URLHandler:
    """Class to handle URL operations."""
    
    def __init__(self, base_url: str = "https://www.edgeprop.my"):
        """Initialize URL handler with base URL."""
        self.base_url = base_url.rstrip('/')  
    
    def get_full_url(self, url: str) -> str:
        """
        Convert relative URL to absolute URL if needed.
        
        Args:
            url: URL string that might be relative
            
        Returns:
            Absolute URL
        """
        if not url:
            return ""
            
        # Check if URL is relative (starts with /)
        if url.startswith('/'):
            return urljoin(self.base_url, url)
            
        # Check if URL is already absolute
        parsed = urlparse(url)
        if parsed.netloc:
            return url
            
        # If URL doesn't start with / but is still relative
        return urljoin(self.base_url, '/' + url)
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        if not url:
            return False
            
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False 