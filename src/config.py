"""
Configuration loader for Drug Discovery Pipeline
"""

import os
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Config:
    """Runtime configuration"""
    provider: Literal["anthropic", "bedrock"]
    api_key: Optional[str]
    aws_region: str
    model: str
    debug: bool


def load_config_from_env() -> Config:
    """
    Load configuration from environment variables.
    
    For Anthropic Direct API:
    - DISCOVERY_PROVIDER=anthropic
    - ANTHROPIC_API_KEY=sk-...
    
    For AWS Bedrock:
    - DISCOVERY_PROVIDER=bedrock
    - AWS_REGION=us-west-2
    - AWS_ACCESS_KEY_ID=...
    - AWS_SECRET_ACCESS_KEY=...
    """
    provider = os.getenv("DISCOVERY_PROVIDER", "anthropic").lower()
    
    if provider not in ["anthropic", "bedrock"]:
        raise ValueError(
            f"Invalid provider: {provider}. Use 'anthropic' or 'bedrock'."
        )
    
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError(
            "Anthropic provider selected but ANTHROPIC_API_KEY not set.\n"
            "Set it with: export ANTHROPIC_API_KEY='sk-...'"
        )
    
    return Config(
        provider=provider,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        aws_region=os.getenv("AWS_REGION", "us-west-2"),
        model=os.getenv("DISCOVERY_MODEL", "claude-3-5-sonnet-20241022"),
        debug=os.getenv("DEBUG", "False").lower() == "true",
    )
