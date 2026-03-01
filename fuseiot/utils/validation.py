from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DeviceModel(BaseModel):
    """Device configuration validation."""
    
    device_id: str = Field(..., min_length=1, max_length=128)
    protocol: str = Field(..., pattern=r"^(http|https|mqtt|mqtts|websocket|serial)$")
    capability: str = Field(..., pattern=r"^(switchable|dimmable|sensor|motor|thermostat|lock|rgb_light|energy_monitor)$")
    endpoint: str
    config: Optional[Dict[str, Any]] = None
    
    @field_validator('endpoint')
    def validate_endpoint(cls, v, info):
        protocol = info.data.get('protocol', '')
        if protocol.startswith('http') and not v.startswith(('http://', 'https://')):
            raise ValueError('HTTP endpoint must start with http:// or https://')
        return v


class CommandModel(BaseModel):
    """Command validation."""
    
    device_id: str
    command: str = Field(..., pattern=r"^(on|off|toggle|set|read|move|lock|unlock)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confirm: bool = True
    timeout: float = Field(default=5.0, gt=0, le=300)


class StateModel(BaseModel):
    """State data validation."""
    
    device_id: str
    timestamp: float
    values: Dict[str, Any]
    source: str = "unknown"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)