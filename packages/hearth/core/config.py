"""
Hearth Core - Configuration Management
"""

import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import yaml


class Config:
    """
    Configuration manager for Hearth.
    Loads from YAML, resolves env vars, provides typed access.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Look in standard locations
            candidates = [
                Path(__file__).parent.parent / "config" / "hearth.yaml",
                Path("/opt/hearth/config/hearth.yaml"),
                Path.home() / ".config" / "hearth" / "hearth.yaml",
            ]
            for candidate in candidates:
                if candidate.exists():
                    config_path = candidate
                    break
            else:
                raise FileNotFoundError("No hearth.yaml found")
        
        self.config_path = Path(config_path)
        self.base_dir = self.config_path.parent.parent
        self._data = self._load()
        
    def _load(self) -> dict:
        """Load and process configuration."""
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        return data
    
    def _resolve_env(self, key: str) -> str:
        """Resolve an environment variable reference."""
        value = os.environ.get(key, "")
        if not value:
            # Try loading from .env file
            env_file = self.base_dir / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith(f"{key}="):
                        value = line.split("=", 1)[1].strip().strip('"\'')
                        break
        return value
    
    def get_api_key(self, model: str) -> str:
        """Get API key for a model."""
        model_config = self._data.get('models', {}).get(model, {})
        env_var = model_config.get('api_key_env', '')
        return self._resolve_env(env_var)
    
    def __getattr__(self, name: str) -> Any:
        """Access config sections as attributes."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name, {})
    
    def __getitem__(self, key: str) -> Any:
        """Access config via bracket notation."""
        return self._data[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a nested config value with dot notation."""
        keys = key.split('.')
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    @property
    def entity_home(self) -> Path:
        """Get the entity's home directory."""
        # Check env var first, then config, then default
        env_home = os.environ.get('ENTITY_HOME')
        if env_home:
            return Path(env_home)
        return Path(self._data.get('entity', {}).get('home', '/home/_'))

    @property
    def soul_path(self) -> Path:
        """Get path to soul.md file."""
        return self.entity_home / "identity" / "soul.md"

    @property
    def user_path(self) -> Path:
        """Get path to user.md file."""
        return self.entity_home / "identity" / "user.md"

    @property
    def reflections_dir(self) -> Path:
        """Get reflections directory."""
        return self.entity_home / "reflections"

    @property
    def data_dir(self) -> Path:
        """Get data directory."""
        return self.entity_home / "data"

    @property
    def xai_key(self) -> str:
        """Get xAI API key."""
        return self.get_api_key("grok")

    @property
    def grok_model(self) -> str:
        """Get Grok model name."""
        return self._data.get('models', {}).get('grok', {}).get('model', 'grok-2-1212')

    @property
    def sonnet_model(self) -> str:
        """Get Sonnet model name."""
        return self._data.get('models', {}).get('sonnet', {}).get('model', 'claude-sonnet-4-5-20250929')

    @property
    def opus_model(self) -> str:
        """Get Opus model name."""
        return self._data.get('models', {}).get('opus', {}).get('model', 'claude-opus-4-5-20251101')

    @property
    def mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._data.get('mock_mode', False)

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._data.get('debug', False)

    @property
    def is_nightshift(self) -> bool:
        """Check if currently in nightshift hours."""
        schedule = self._data.get('schedule', {}).get('nightshift', {})
        if not schedule.get('enabled', False):
            return False
            
        now = datetime.now()
        start = schedule.get('start', '22:00')
        end = schedule.get('end', '06:00')
        
        start_h, start_m = map(int, start.split(':'))
        end_h, end_m = map(int, end.split(':'))
        
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m
        current_mins = now.hour * 60 + now.minute
        
        # Handle overnight wrap
        if start_mins > end_mins:
            return current_mins >= start_mins or current_mins < end_mins
        return start_mins <= current_mins < end_mins
    
    @property
    def current_interval(self) -> int:
        """Get current check interval in minutes."""
        if self.is_nightshift:
            return self._data.get('schedule', {}).get('nightshift', {}).get('interval_minutes', 2)
        return self._data.get('schedule', {}).get('dayshift', {}).get('interval_minutes', 10)
    
    def is_quiet_hours(self) -> bool:
        """Check if in quiet hours for notifications."""
        quiet = self._data.get('telegram', {}).get('quiet_hours', {})
        if not quiet.get('enabled', False):
            return False
            
        now = datetime.now()
        start = quiet.get('start', '23:00')
        end = quiet.get('end', '07:00')
        
        start_h, start_m = map(int, start.split(':'))
        end_h, end_m = map(int, end.split(':'))
        
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m
        current_mins = now.hour * 60 + now.minute
        
        if start_mins > end_mins:
            return current_mins >= start_mins or current_mins < end_mins
        return start_mins <= current_mins < end_mins


# Global instance
_config: Optional[Config] = None

def get_config(config_path: Optional[str] = None) -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
