"""
Configuration loader for the activity reporting system.

Handles loading configuration from YAML files and environment variables.
Supports .env files for sensitive credentials and secrets.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class ConfigLoader:
    """
    Load and manage configuration from YAML and environment variables.

    This class loads configuration from a YAML file and merges it with
    environment variables. Secrets should be stored in .env file.

    Attributes:
        config: Dictionary containing all configuration values

    Example:
        >>> config_loader = ConfigLoader('config/config.yaml')
        >>> smtp_host = config_loader.get('email.smtp_host')
    """

    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to YAML configuration file
            env_path: Path to .env file (default: .env in project root)

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        self.config: Dict[str, Any] = {}

        # Load environment variables from .env file
        if env_path:
            load_dotenv(env_path)
        else:
            # Try to find .env in current directory or parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                env_file = parent / '.env'
                if env_file.exists():
                    load_dotenv(env_file)
                    break

        # Load YAML configuration
        if config_path:
            self._load_yaml_config(config_path)

        # Override with environment variables
        self._load_env_overrides()

    def _load_yaml_config(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}

    def _load_env_overrides(self) -> None:
        """
        Load environment variable overrides.

        Environment variables in format: REPORTPILOT_SECTION_KEY=value
        Example: REPORTPILOT_EMAIL_SMTP_HOST=smtp.gmail.com
        """
        prefix = 'REPORTPILOT_'

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to nested dict structure
                config_key = key[len(prefix):].lower()
                parts = config_key.split('_')

                # Navigate/create nested dict structure
                current = self.config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set the value (convert to appropriate type)
                current[parts[-1]] = self._convert_value(value)

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False

        # Numeric conversion
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'email.smtp_host')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('email.smtp_host', 'smtp.gmail.com')
        """
        parts = key.split('.')
        current = self.config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def get_required(self, key: str) -> Any:
        """
        Get required configuration value.

        Args:
            key: Configuration key in dot notation

        Returns:
            Configuration value

        Raises:
            ValueError: If required key is not found
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required configuration key not found: {key}")
        return value

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get value from environment variable.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)

    def get_env_required(self, key: str) -> str:
        """
        Get required environment variable.

        Args:
            key: Environment variable name

        Returns:
            Environment variable value

        Raises:
            ValueError: If required variable is not found
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable not found: {key}")
        return value
