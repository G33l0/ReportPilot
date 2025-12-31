"""
API data reader for the activity reporting system.

Reads data from REST APIs with support for authentication and pagination.
"""

import pandas as pd
import requests
from typing import Dict, Any, List, Optional
from .base import DataReader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class APIReader(DataReader):
    """
    Read data from REST APIs.

    Configuration parameters:
        - url: API endpoint URL (required)
        - method: HTTP method (default: 'GET')
        - auth_type: Authentication type ('bearer', 'basic', 'api_key', None)
        - auth_token: Authentication token (if auth_type is 'bearer' or 'api_key')
        - auth_username: Username (if auth_type is 'basic')
        - auth_password: Password (if auth_type is 'basic')
        - headers: Custom headers dictionary
        - params: Query parameters dictionary
        - data_path: JSON path to data array (e.g., 'data.items')
        - timeout: Request timeout in seconds (default: 30)
        - verify_ssl: Verify SSL certificates (default: True)

    Example:
        >>> config = {
        ...     'url': 'https://api.example.com/activities',
        ...     'auth_type': 'bearer',
        ...     'auth_token': 'your-token',
        ...     'data_path': 'data'
        ... }
        >>> reader = APIReader(config)
        >>> df = reader.read()
    """

    def validate_config(self) -> None:
        """Validate API reader configuration."""
        if 'url' not in self.source_config:
            raise ValueError("API reader requires 'url' in configuration")

        auth_type = self.source_config.get('auth_type')
        if auth_type == 'bearer' and 'auth_token' not in self.source_config:
            raise ValueError("Bearer auth requires 'auth_token' in configuration")
        if auth_type == 'basic':
            if 'auth_username' not in self.source_config or 'auth_password' not in self.source_config:
                raise ValueError("Basic auth requires 'auth_username' and 'auth_password'")

    def read(self) -> pd.DataFrame:
        """
        Read data from API endpoint.

        Returns:
            DataFrame containing the API data

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response cannot be parsed
        """
        url = self.source_config['url']
        method = self.source_config.get('method', 'GET').upper()
        timeout = self.source_config.get('timeout', 30)
        verify_ssl = self.source_config.get('verify_ssl', True)

        # Prepare headers
        headers = self.source_config.get('headers', {}).copy()

        # Add authentication
        auth = None
        auth_type = self.source_config.get('auth_type')

        if auth_type == 'bearer':
            headers['Authorization'] = f"Bearer {self.source_config['auth_token']}"
        elif auth_type == 'api_key':
            headers['X-API-Key'] = self.source_config['auth_token']
        elif auth_type == 'basic':
            auth = (
                self.source_config['auth_username'],
                self.source_config['auth_password']
            )

        # Query parameters
        params = self.source_config.get('params', {})

        logger.info(f"Requesting data from API: {url}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                auth=auth,
                timeout=timeout,
                verify=verify_ssl
            )

            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract data from nested path if specified
            data_path = self.source_config.get('data_path')
            if data_path:
                for key in data_path.split('.'):
                    data = data[key]

            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # If single object, wrap in list
                df = pd.DataFrame([data])
            else:
                raise ValueError(f"Unexpected API response type: {type(data)}")

            logger.info(f"Successfully retrieved {len(df)} rows from API")
            return df

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise
