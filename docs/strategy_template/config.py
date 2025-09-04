"""
Example template for creating a new prompt retrieval strategy.

Copy this template to create new strategies:
1. Copy this entire directory to strategies/your_strategy_name/
2. Rename the files and classes appropriately
3. Implement the strategy logic
4. Add your strategy to strategies/__init__.py
"""

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True) 
class ExampleStrategyConfig:
    """Configuration for the example strategy."""
    
    # Add your configuration fields here
    api_endpoint: str
    api_key: str
    timeout_seconds: Optional[int] = 30
    
    # Add validation if needed
    def __post_init__(self):
        if not self.api_endpoint:
            raise ValueError("api_endpoint is required")
        if not self.api_key:
            raise ValueError("api_key is required")
