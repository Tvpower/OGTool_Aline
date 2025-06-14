"""
Configuration loader for the web scraper tool.
Handles loading and validating YAML configuration files.
"""

import yaml
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ScrapingTarget:
    """Represents a single scraping target with its configuration."""
    name: str
    url: str
    type: str
    enabled: bool = True
    article_link_selector: str = ""
    article_link_filter: str = ""
    title_selector: str = "h1"
    content_selectors: List[str] = None
    author_selector: str = ""
    author_extraction: str = ""
    default_author: str = ""
    content_elements: List[str] = None
    content_min_length: int = 50
    exclude_content_patterns: List[str] = None
    discovery_pages: List[str] = None

    def __post_init__(self):
        if self.content_selectors is None:
            self.content_selectors = []
        if self.content_elements is None:
            self.content_elements = []
        if self.exclude_content_patterns is None:
            self.exclude_content_patterns = []
        if self.discovery_pages is None:
            self.discovery_pages = []


@dataclass
class ScraperConfig:
    """Main configuration class for the scraper."""
    output_file: str = "output.json"
    team_id: str = "aline123"
    pdf_directory: str = "Books_PDF"
    max_workers: int = 3
    request_delay: float = 0.2
    timeout: int = 15
    headers: Dict[str, str] = None
    targets: List[ScrapingTarget] = None
    site_configs: Dict[str, Any] = None
    pdf_processing: Dict[str, Any] = None
    zenrows_config: Dict[str, Any] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        if self.targets is None:
            self.targets = []
        if self.site_configs is None:
            self.site_configs = {}
        if self.pdf_processing is None:
            self.pdf_processing = {'enabled': True}
        if self.zenrows_config is None:
            self.zenrows_config = {'enabled': False}


class ConfigLoader:
    """Handles loading and parsing configuration files."""
    
    @staticmethod
    def load_config(config_path: str) -> ScraperConfig:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            ScraperConfig object with loaded configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config file is missing required fields
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in config file: {e}")
        
        if not config_data:
            raise ValueError("Configuration file is empty")
        
        return ConfigLoader._parse_config(config_data)
    
    @staticmethod
    def _parse_config(config_data: Dict[str, Any]) -> ScraperConfig:
        """Parse the loaded configuration data into a ScraperConfig object."""
        
        # Extract global settings
        settings = config_data.get('settings', {})
        headers = config_data.get('headers', {})
        site_configs = config_data.get('site_configs', {})
        pdf_processing = config_data.get('pdf_processing', {})
        zenrows_config = config_data.get('zenrows', {})
        
        # Parse targets
        targets = []
        for target_data in config_data.get('targets', []):
            target = ScrapingTarget(
                name=target_data.get('name', ''),
                url=target_data.get('url', ''),
                type=target_data.get('type', 'blog'),
                enabled=target_data.get('enabled', True),
                article_link_selector=target_data.get('article_link_selector', ''),
                article_link_filter=target_data.get('article_link_filter', ''),
                title_selector=target_data.get('title_selector', 'h1'),
                content_selectors=target_data.get('content_selectors', []),
                author_selector=target_data.get('author_selector', ''),
                author_extraction=target_data.get('author_extraction', ''),
                default_author=target_data.get('default_author', ''),
                content_elements=target_data.get('content_elements', []),
                content_min_length=target_data.get('content_min_length', 50),
                exclude_content_patterns=target_data.get('exclude_content_patterns', []),
                discovery_pages=target_data.get('discovery_pages', [])
            )
            targets.append(target)
        
        # Create main config object
        config = ScraperConfig(
            output_file=settings.get('output_file', 'output.json'),
            team_id=settings.get('team_id', 'aline123'),
            pdf_directory=settings.get('pdf_directory', 'Books_PDF'),
            max_workers=settings.get('max_workers', 3),
            request_delay=settings.get('request_delay', 0.2),
            timeout=settings.get('timeout', 15),
            headers=headers,
            targets=targets,
            site_configs=site_configs,
            pdf_processing=pdf_processing,
            zenrows_config=zenrows_config
        )
        
        return config
    
    @staticmethod
    def get_enabled_targets(config: ScraperConfig) -> List[ScrapingTarget]:
        """Get only the enabled scraping targets from the configuration."""
        return [target for target in config.targets if target.enabled]
    
    @staticmethod
    def get_target_by_name(config: ScraperConfig, name: str) -> Optional[ScrapingTarget]:
        """Get a specific target by name."""
        for target in config.targets:
            if target.name.lower() == name.lower():
                return target
        return None
    
    @staticmethod
    def validate_config(config: ScraperConfig) -> List[str]:
        """
        Validate the configuration and return a list of validation errors.
        
        Returns:
            List of error messages, empty if config is valid
        """
        errors = []
        
        if not config.team_id:
            errors.append("team_id is required in settings")
        
        if not config.output_file:
            errors.append("output_file is required in settings")
        
        if config.max_workers < 1:
            errors.append("max_workers must be at least 1")
        
        if config.request_delay < 0:
            errors.append("request_delay must be non-negative")
        
        for i, target in enumerate(config.targets):
            if not target.name:
                errors.append(f"Target {i+1}: name is required")
            
            if not target.url:
                errors.append(f"Target '{target.name}': url is required")
            
            if not target.type:
                errors.append(f"Target '{target.name}': type is required")
        
        return errors 