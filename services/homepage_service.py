"""
Homepage Content Management Service
Handles loading, updating, and validating homepage content configuration
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class HomepageService:
    """Service for managing homepage content configuration"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config" / "homepage_content.json"
        self._cache = None
    
    def get_content(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get homepage content configuration
        
        Args:
            use_cache: Whether to use cached content (default: True)
            
        Returns:
            Dictionary containing homepage content configuration
        """
        if use_cache and self._cache is not None:
            return self._cache
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # Validate content structure
            self._validate_content(content)
            
            if use_cache:
                self._cache = content
                
            return content
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Homepage content file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in homepage content file: {e}")
    
    def update_content(self, content: Dict[str, Any]) -> bool:
        """
        Update homepage content configuration
        
        Args:
            content: New content configuration
            
        Returns:
            True if update was successful
        """
        # Validate content before saving
        self._validate_content(content)
        
        try:
            # Create backup of current content
            self._create_backup()
            
            # Write new content
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            
            # Clear cache to force reload
            self._cache = None
            
            return True
            
        except Exception as e:
            # Restore from backup if write failed
            self._restore_backup()
            raise Exception(f"Failed to update homepage content: {e}")
    
    def update_section(self, section: str, section_content: Dict[str, Any]) -> bool:
        """
        Update a specific section of homepage content
        
        Args:
            section: Section name (e.g., 'hero', 'pricing')
            section_content: New content for the section
            
        Returns:
            True if update was successful
        """
        current_content = self.get_content(use_cache=False)
        current_content[section] = section_content
        
        return self.update_content(current_content)
    
    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Get content for a specific section
        
        Args:
            section: Section name
            
        Returns:
            Section content or None if not found
        """
        content = self.get_content()
        return content.get(section)
    
    def _validate_content(self, content: Dict[str, Any]) -> None:
        """
        Validate homepage content structure
        
        Args:
            content: Content to validate
            
        Raises:
            ValueError: If content structure is invalid
        """
        required_sections = ['hero', 'problem', 'solution', 'features', 'daily_brief', 'pricing', 'footer']
        
        for section in required_sections:
            if section not in content:
                raise ValueError(f"Missing required section: {section}")
        
        # Validate hero section
        hero = content.get('hero', {})
        required_hero_fields = ['headline', 'subheadline', 'cta_text', 'cta_link']
        for field in required_hero_fields:
            if field not in hero:
                raise ValueError(f"Missing required hero field: {field}")
        
        # Validate pricing section
        pricing = content.get('pricing', {})
        if 'plans' not in pricing or not isinstance(pricing['plans'], list):
            raise ValueError("Pricing section must contain a 'plans' list")
        
        for plan in pricing['plans']:
            required_plan_fields = ['name', 'price', 'description', 'features', 'cta']
            for field in required_plan_fields:
                if field not in plan:
                    raise ValueError(f"Missing required pricing plan field: {field}")
    
    def _create_backup(self) -> None:
        """Create backup of current content file"""
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.json.backup')
            import shutil
            shutil.copy2(self.config_path, backup_path)
    
    def _restore_backup(self) -> None:
        """Restore content from backup file"""
        backup_path = self.config_path.with_suffix('.json.backup')
        if backup_path.exists():
            import shutil
            shutil.copy2(backup_path, self.config_path)
    
    def get_editable_sections(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about editable sections for admin interface
        
        Returns:
            Dictionary mapping section names to their metadata
        """
        return {
            'hero': {
                'name': 'Hero Section',
                'description': 'Main headline and call-to-action',
                'fields': 'headline, subheadline, cta_text, cta_link'
            },
            'problem': {
                'name': 'Problem Section', 
                'description': 'Challenges that CTOs face',
                'fields': 'headline, subheadline, challenges'
            },
            'solution': {
                'name': 'Solution Section',
                'description': 'Attention Engine explanation',
                'fields': 'title, description, workflow'
            },
            'features': {
                'name': 'Features Section',
                'description': 'Product features and integrations',
                'fields': 'title, subtitle, items'
            },
            'daily_brief': {
                'name': 'Daily Brief Example',
                'description': 'Sample CTO briefing display',
                'fields': 'title, subtitle, items, cta'
            },
            'pricing': {
                'name': 'Pricing Section',
                'description': 'Pricing plans and CTAs',
                'fields': 'title, subtitle, plans, bottom_cta'
            },
            'footer': {
                'name': 'Footer',
                'description': 'Footer links and information',
                'fields': 'tagline, sections, social_links, copyright'
            }
        }


# Global instance for easy import
homepage_service = HomepageService()