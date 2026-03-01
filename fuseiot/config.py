import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

from fuseiot.exceptions import ConfigurationError, ValidationError
from fuseiot.logging_config import get_logger

logger = get_logger("config")


@dataclass
class Config:
    """FuseIoT configuration."""
    
    # Hub settings
    default_ttl: float = 5.0
    max_devices: int = 1000
    
    # Protocol defaults
    default_timeout: float = 5.0
    default_retry_attempts: int = 3
    
    # Confirmation settings
    confirm_default: bool = True
    confirm_timeout: float = 2.0
    confirm_poll_interval: float = 0.1
    confirm_max_attempts: int = 20
    
    # Resilience
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: float = 30.0
    
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: float = 60.0
    
    # Persistence
    persistence_enabled: bool = False
    persistence_backend: str = "sqlite"  # sqlite, redis, memory
    persistence_path: Optional[str] = "fuseiot.db"
    redis_url: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_json: bool = False
    log_file: Optional[str] = None
    
    # Security
    tls_verify: bool = True
    tls_ca_bundle: Optional[str] = None
    
    # Cloud
    cloud_enabled: bool = False
    cloud_provider: Optional[str] = None  # aws, azure, gcp
    
    # Metadata
    environment: str = "development"
    tags: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create from dictionary."""
        # Filter to only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }


def from_yaml(path: Union[str, Path]) -> Config:
    """Load configuration from YAML file."""
    path = Path(path)
    if not path.exists():
        raise ConfigurationError(f"Config file not found: {path}")
    
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        logger.info("config_loaded", source=str(path), format="yaml")
        return Config.from_dict(data or {})
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {path}: {e}")


def from_json(path: Union[str, Path]) -> Config:
    """Load configuration from JSON file."""
    path = Path(path)
    if not path.exists():
        raise ConfigurationError(f"Config file not found: {path}")
    
    try:
        with open(path) as f:
            data = json.load(f)
        logger.info("config_loaded", source=str(path), format="json")
        return Config.from_dict(data)
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in {path}: {e}")


def from_env(prefix: str = "FUSEIOT_") -> Config:
    """Load configuration from environment variables."""
    env_vars = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # Convert FUSEIOT_DEFAULT_TTL -> default_ttl
            config_key = key[len(prefix):].lower().replace("__", ".")
            
            # Type conversion
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
            
            env_vars[config_key] = value
    
    logger.info("config_loaded", source="environment", vars_count=len(env_vars))
    return Config.from_dict(env_vars)


def auto_config(
    config_path: Optional[str] = None,
    env_prefix: str = "FUSEIOT_"
) -> Config:
    """
    Auto-detect configuration from multiple sources (priority: env > file > defaults).
    
    Args:
        config_path: Path to YAML or JSON config file
        env_prefix: Prefix for environment variables
    
    Returns:
        Merged configuration
    """
    # Start with defaults
    config = Config()
    
    # Load from file if provided
    if config_path:
        path = Path(config_path)
        if path.suffix in (".yaml", ".yml"):
            file_config = from_yaml(path)
        elif path.suffix == ".json":
            file_config = from_json(path)
        else:
            raise ConfigurationError(f"Unknown config format: {path.suffix}")
        
        # Merge file config
        for key, value in file_config.to_dict().items():
            if value is not None:  # Don't override with None
                setattr(config, key, value)
    
    # Environment variables override everything
    env_config = from_env(env_prefix)
    for key, value in env_config.to_dict().items():
        # Only override if env var was actually set (not default)
        env_key = f"{env_prefix}{key.upper()}"
        if env_key in os.environ:
            setattr(config, key, value)
    
    logger.info("config_resolved", 
                file=config_path, 
                environment=config.environment,
                log_level=config.log_level)
    
    return config