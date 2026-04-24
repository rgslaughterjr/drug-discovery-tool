"""Model discovery endpoint."""

from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(prefix="/api/models", tags=["models"])


# Hardcoded model data (updated 2026)
MODELS_DATA = {
    "anthropic": [
        {
            "id": "claude-3-5-sonnet-20241022",
            "name": "Claude 3.5 Sonnet",
            "context_window": 200000,
            "released": "2024-10-22",
            "cost_input_per_1m": 3.00,
            "cost_output_per_1m": 15.00,
            "capabilities": ["text", "tool-use"],
            "recommended": True,
        },
        {
            "id": "claude-3-opus-20250219",
            "name": "Claude 3 Opus",
            "context_window": 200000,
            "released": "2025-02-19",
            "cost_input_per_1m": 15.00,
            "cost_output_per_1m": 75.00,
            "capabilities": ["text", "tool-use"],
            "recommended": True,
        },
        {
            "id": "claude-3-haiku-20240307",
            "name": "Claude 3 Haiku",
            "context_window": 200000,
            "released": "2024-03-07",
            "cost_input_per_1m": 0.80,
            "cost_output_per_1m": 4.00,
            "capabilities": ["text"],
            "recommended": False,
        },
    ],
    "openai": [
        {
            "id": "gpt-4o",
            "name": "GPT-4o",
            "context_window": 128000,
            "released": "2024-11-01",
            "cost_input_per_1m": 5.00,
            "cost_output_per_1m": 15.00,
            "capabilities": ["text", "vision"],
            "recommended": True,
        },
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "context_window": 128000,
            "released": "2024-04-09",
            "cost_input_per_1m": 10.00,
            "cost_output_per_1m": 30.00,
            "capabilities": ["text", "vision"],
            "recommended": False,
        },
        {
            "id": "o1",
            "name": "O1",
            "context_window": 128000,
            "released": "2024-12-20",
            "cost_input_per_1m": 15.00,
            "cost_output_per_1m": 60.00,
            "capabilities": ["text", "reasoning"],
            "recommended": False,
        },
    ],
    "google": [
        {
            "id": "gemini-2.0-flash",
            "name": "Gemini 2.0 Flash",
            "context_window": 1000000,
            "released": "2024-12-19",
            "cost_input_per_1m": 0.075,
            "cost_output_per_1m": 0.30,
            "capabilities": ["text", "vision", "audio"],
            "recommended": True,
        },
        {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "context_window": 2000000,
            "released": "2024-06-18",
            "cost_input_per_1m": 1.25,
            "cost_output_per_1m": 5.00,
            "capabilities": ["text", "vision"],
            "recommended": True,
        },
        {
            "id": "gemini-1.5-flash",
            "name": "Gemini 1.5 Flash",
            "context_window": 1000000,
            "released": "2024-05-14",
            "cost_input_per_1m": 0.075,
            "cost_output_per_1m": 0.30,
            "capabilities": ["text", "vision"],
            "recommended": False,
        },
    ],
    "cohere": [
        {
            "id": "command-r-plus",
            "name": "Command R Plus",
            "context_window": 128000,
            "released": "2024-03-28",
            "cost_input_per_1m": 3.00,
            "cost_output_per_1m": 15.00,
            "capabilities": ["text"],
            "recommended": True,
        },
        {
            "id": "command-r",
            "name": "Command R",
            "context_window": 128000,
            "released": "2024-03-28",
            "cost_input_per_1m": 0.50,
            "cost_output_per_1m": 1.50,
            "capabilities": ["text"],
            "recommended": False,
        },
    ],
    "mistral": [
        {
            "id": "mistral-large",
            "name": "Mistral Large",
            "context_window": 128000,
            "released": "2024-02-27",
            "cost_input_per_1m": 2.00,
            "cost_output_per_1m": 6.00,
            "capabilities": ["text"],
            "recommended": True,
        },
        {
            "id": "mistral-medium",
            "name": "Mistral Medium",
            "context_window": 32000,
            "released": "2023-12-11",
            "cost_input_per_1m": 0.27,
            "cost_output_per_1m": 0.81,
            "capabilities": ["text"],
            "recommended": False,
        },
    ],
}


@router.get("/available")
async def get_available_models() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get list of available models from top LLM providers.
    Includes context window, cost estimates, capabilities, and recommendations.
    """
    return MODELS_DATA
