"""
API Client for Drug Discovery Pipeline
Supports multiple LLM providers: Anthropic, AWS Bedrock, OpenAI, Cohere, Ollama, Together, and any OpenAI-compatible API
"""

import json
from typing import Optional, Any
from dataclasses import dataclass
import os


@dataclass
class APIConfig:
    """Configuration for API provider (LLM-agnostic)"""
    provider: str = "anthropic"  # 'anthropic', 'bedrock', 'openai', 'cohere', 'ollama', 'together', or custom endpoint
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"  # Model ID (provider-specific)
    base_url: Optional[str] = None  # For OpenAI-compatible APIs and custom endpoints
    aws_region: str = "us-west-2"  # Only used for Bedrock

    def __post_init__(self):
        """Validate and normalize provider name"""
        if not self.provider:
            raise ValueError("Provider must be specified")
        self.provider = self.provider.lower().strip()


class DrugDiscoveryClient:
    """
    Unified client for drug discovery workflows.

    Supports multiple LLM providers:
    - Anthropic Direct API
    - AWS Bedrock
    - OpenAI (including Azure OpenAI with custom base_url)
    - Cohere
    - Ollama (local LLMs)
    - Together.ai
    - Any OpenAI-compatible API endpoint

    Provider-agnostic architecture allows seamless switching between LLM backends.
    """

    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize client from config or environment variables.

        Environment variables:
        - DISCOVERY_PROVIDER: Provider name (default: 'anthropic')
          Supported: 'anthropic', 'bedrock', 'openai', 'cohere', 'ollama', 'together'
        - DISCOVERY_API_KEY or provider-specific key: API credential
          - ANTHROPIC_API_KEY for Anthropic
          - OPENAI_API_KEY for OpenAI
          - COHERE_API_KEY for Cohere
          - TOGETHER_API_KEY for Together.ai
          - Ollama: not required (local)
        - DISCOVERY_MODEL: Model ID (provider-specific, default: claude-3-5-sonnet-20241022)
        - DISCOVERY_BASE_URL: Custom API endpoint (for OpenAI-compatible or custom providers)
        - AWS_REGION: For Bedrock only (default: 'us-west-2')

        Args:
            config: Optional APIConfig instance. If None, loads from environment.
        """
        if config is None:
            # Load from environment with smart API key detection
            api_key = (
                os.getenv("DISCOVERY_API_KEY") or
                os.getenv("ANTHROPIC_API_KEY") or
                os.getenv("OPENAI_API_KEY") or
                os.getenv("COHERE_API_KEY") or
                os.getenv("TOGETHER_API_KEY")
            )

            config = APIConfig(
                provider=os.getenv("DISCOVERY_PROVIDER", "anthropic"),
                api_key=api_key,
                model=os.getenv("DISCOVERY_MODEL", "claude-3-5-sonnet-20241022"),
                base_url=os.getenv("DISCOVERY_BASE_URL"),
                aws_region=os.getenv("AWS_REGION", "us-west-2"),
            )

        self.config = config
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate API client using factory pattern"""
        provider = self.config.provider

        if provider == "anthropic":
            self._init_anthropic()
        elif provider == "bedrock":
            self._init_bedrock()
        elif provider == "openai":
            self._init_openai()
        elif provider == "cohere":
            self._init_cohere()
        elif provider == "ollama":
            self._init_ollama()
        elif provider == "together":
            self._init_together()
        else:
            # Attempt generic OpenAI-compatible API
            self._init_openai_compatible()

    def _init_anthropic(self):
        """Initialize Anthropic Direct API client"""
        from anthropic import Anthropic
        if not self.config.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Provide via: APIConfig(api_key='sk-ant-...') or export ANTHROPIC_API_KEY='sk-...'"
            )
        self.client = Anthropic(api_key=self.config.api_key)
        self.model_id = self.config.model
        self.provider_type = "anthropic"

    def _init_bedrock(self):
        """Initialize AWS Bedrock client"""
        import boto3
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=self.config.aws_region
        )
        # Bedrock model ID mapping
        bedrock_model_map = {
            "claude-3-5-sonnet-20241022": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
            "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        }
        self.model_id = bedrock_model_map.get(self.config.model, self.config.model)
        self.provider_type = "bedrock"

    def _init_openai(self):
        """Initialize OpenAI API client (or OpenAI-compatible)"""
        from openai import OpenAI
        if not self.config.api_key:
            raise ValueError(
                "API key not set for OpenAI. "
                "Provide via: APIConfig(api_key='sk-...') or export OPENAI_API_KEY='sk-...'"
            )
        base_url = self.config.base_url or "https://api.openai.com/v1"
        self.client = OpenAI(api_key=self.config.api_key, base_url=base_url)
        self.model_id = self.config.model
        self.provider_type = "openai"

    def _init_cohere(self):
        """Initialize Cohere API client"""
        from cohere import Client
        if not self.config.api_key:
            raise ValueError(
                "COHERE_API_KEY not set. "
                "Provide via: APIConfig(api_key='...') or export COHERE_API_KEY='...'"
            )
        self.client = Client(api_key=self.config.api_key)
        self.model_id = self.config.model or "command-r-plus"
        self.provider_type = "cohere"

    def _init_ollama(self):
        """Initialize Ollama client (local LLM)"""
        from openai import OpenAI
        base_url = self.config.base_url or "http://localhost:11434/v1"
        self.client = OpenAI(
            api_key="ollama",  # Dummy key; Ollama doesn't require auth
            base_url=base_url
        )
        self.model_id = self.config.model or "llama2"
        self.provider_type = "ollama"

    def _init_together(self):
        """Initialize Together.ai API client"""
        from openai import OpenAI
        if not self.config.api_key:
            raise ValueError(
                "TOGETHER_API_KEY not set. "
                "Provide via: APIConfig(api_key='...') or export TOGETHER_API_KEY='...'"
            )
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url="https://api.together.xyz/v1"
        )
        self.model_id = self.config.model or "meta-llama/Llama-2-7b-chat-hf"
        self.provider_type = "together"

    def _init_openai_compatible(self):
        """Initialize generic OpenAI-compatible API client"""
        from openai import OpenAI
        if not self.config.api_key:
            raise ValueError(
                f"API key not set for provider '{self.config.provider}'. "
                "Provide via: APIConfig(api_key='...') or appropriate environment variable."
            )
        if not self.config.base_url:
            raise ValueError(
                f"base_url required for provider '{self.config.provider}'. "
                "Provide via: APIConfig(base_url='https://...')"
            )
        self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
        self.model_id = self.config.model
        self.provider_type = "openai_compatible"

    def evaluate_target(
        self,
        organism: str,
        protein_name: str,
        protein_id: Optional[str] = None,
    ) -> dict:
        """
        Evaluate a protein as a drug target.
        
        Args:
            organism: Bacterial or protozoan species (e.g., "Staphylococcus aureus")
            protein_name: Common or systematic protein name (e.g., "GyrB", "DNA gyrase")
            protein_id: UniProt ID or PDB code (optional, for faster lookups)
            
        Returns:
            Dictionary with GO/NO-GO recommendation and detailed criteria assessment
        """
        system_prompt = self._load_prompt("evaluate_target")

        user_message = f"""
Evaluate the following protein as a drug target for a computational and wet-lab drug discovery project:

**Organism:** {organism}
**Protein:** {protein_name}
{f"**Protein ID (UniProt/PDB):** {protein_id}" if protein_id else ""}

Provide a structured GO/NO-GO recommendation with detailed assessment of all five criteria.
"""

        response = self._call_api(
            system_prompt=system_prompt,
            user_message=user_message,
        )

        return {
            "task": "evaluate_target",
            "organism": organism,
            "protein": protein_name,
            "response": response,
        }

    def get_controls(
        self,
        organism: str,
        protein_name: str,
        pdb_id: str,
    ) -> dict:
        """
        Generate 10 positive and 10 negative controls for docking validation.
        
        Args:
            organism: Species containing the target protein
            protein_name: Name of the target protein
            pdb_id: PDB structure ID (e.g., "4P8O")
            
        Returns:
            Dictionary with positive controls table and negative controls table
        """
        system_prompt = self._load_prompt("get_controls")

        user_message = f"""
Generate validation controls for the following target:

**Organism:** {organism}
**Protein:** {protein_name}
**PDB ID:** {pdb_id}

Provide:
1. 10 positive controls (known binders) with IC50/Ki data and SMILES strings
2. 10 property-matched negative controls (decoys)

Include PubChem CIDs, molecular weights, cLogP, and literature references.
Format as structured JSON with validation flags.
"""

        response = self._call_api(
            system_prompt=system_prompt,
            user_message=user_message,
        )

        return {
            "task": "get_controls",
            "organism": organism,
            "protein": protein_name,
            "pdb_id": pdb_id,
            "response": response,
        }

    def prep_screening(
        self,
        organism: str,
        protein_name: str,
        pdb_id: str,
        mechanism: str,
        docking_software: Optional[str] = None,
    ) -> dict:
        """
        Prepare a ChemBridge Diversity library screening campaign.
        
        Args:
            organism: Target organism
            protein_name: Target protein
            pdb_id: PDB structure ID
            mechanism: Binding mechanism (e.g., "competitive NADPH inhibition")
            docking_software: Docking software to be used (Vina, DOCK6, Glide, rDock)
            
        Returns:
            Dictionary with screening brief and ZINC query parameters
        """
        system_prompt = self._load_prompt("chembridge_prep")

        user_message = f"""
Prepare a screening campaign for the following target:

**Organism:** {organism}
**Protein:** {protein_name}
**PDB ID:** {pdb_id}
**Binding Mechanism:** {mechanism}
{f"**Docking Software:** {docking_software}" if docking_software else ""}

Generate:
1. Pharmacophore analysis (ranked features)
2. Physicochemical filter cutoffs
3. PAINS exclusion rules
4. ZINC20 query parameters with estimated library sizes
5. Post-screening hit prioritization strategy
"""

        response = self._call_api(
            system_prompt=system_prompt,
            user_message=user_message,
        )

        return {
            "task": "prep_screening",
            "organism": organism,
            "protein": protein_name,
            "pdb_id": pdb_id,
            "mechanism": mechanism,
            "response": response,
        }

    def analyze_hits(
        self,
        protein_name: str,
        num_compounds: int,
        docking_scores_summary: str,
        positive_controls_affinity: Optional[str] = None,
    ) -> dict:
        """
        Analyze and prioritize hits from virtual screening.
        
        Args:
            protein_name: Name of the target protein
            num_compounds: Number of compounds screened
            docking_scores_summary: Summary of docking score distribution
            positive_controls_affinity: Affinity data for positive controls (for comparison)
            
        Returns:
            Dictionary with hit prioritization and purchase recommendations
        """
        system_prompt = self._load_prompt("hit_analysis")

        user_message = f"""
Analyze screening hits for the {protein_name} target:

**Compounds Screened:** {num_compounds}
**Docking Scores:** {docking_scores_summary}
{f"**Positive Control Affinities:** {positive_controls_affinity}" if positive_controls_affinity else ""}

Provide:
1. Score cutoff determination
2. Murcko scaffold clustering
3. PAINS re-filtering
4. Selectivity cross-check strategy
5. Prioritized purchase list (top 10-20 compounds)
6. Visual inspection checklist

Format output for direct use in lab notebook entry.
"""

        response = self._call_api(
            system_prompt=system_prompt,
            user_message=user_message,
        )

        return {
            "task": "analyze_hits",
            "protein": protein_name,
            "num_screened": num_compounds,
            "response": response,
        }

    def _call_api(self, system_prompt: str, user_message: str) -> str:
        """
        Call the underlying API (provider-agnostic router).
        Supports: Anthropic, Bedrock, OpenAI, Cohere, Ollama, Together, and OpenAI-compatible APIs
        """
        if self.config.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_message)
        elif self.config.provider == "bedrock":
            return self._call_bedrock(system_prompt, user_message)
        elif self.config.provider == "cohere":
            return self._call_cohere(system_prompt, user_message)
        else:
            # OpenAI-compatible API (openai, ollama, together, or custom endpoint)
            return self._call_openai_compatible(system_prompt, user_message)

    def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Call Anthropic API directly"""
        message = self.client.messages.create(
            model=self.model_id,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text

    def _call_bedrock(self, system_prompt: str, user_message: str) -> str:
        """Call AWS Bedrock API"""
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-06-01",
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            }),
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    def _call_openai_compatible(self, system_prompt: str, user_message: str) -> str:
        """Call OpenAI-compatible API (OpenAI, Ollama, Together, custom endpoint, etc.)"""
        response = self.client.chat.completions.create(
            model=self.model_id,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def _call_cohere(self, system_prompt: str, user_message: str) -> str:
        """Call Cohere API"""
        full_message = f"{system_prompt}\n\n{user_message}"
        response = self.client.generate(
            prompt=full_message,
            model=self.model_id,
            max_tokens=2000,
        )
        return response.generations[0].text

    def _load_prompt(self, task_name: str) -> str:
        """Load system prompt for a task"""
        prompt_dir = os.path.join(
            os.path.dirname(__file__), "..", "prompts"
        )
        prompt_path = os.path.join(prompt_dir, f"{task_name}_system.txt")

        if not os.path.exists(prompt_path):
            # Fallback to generic prompt if specific one doesn't exist
            return self._get_generic_prompt(task_name)

        with open(prompt_path, "r") as f:
            return f.read()

    def _get_generic_prompt(self, task_name: str) -> str:
        """Fallback generic prompts for each task"""
        prompts = {
            "evaluate_target": (
                "You are an expert computational biochemist evaluating proteins as drug targets. "
                "Assess using five criteria: (1) Essentiality, (2) Structural availability, "
                "(3) Biochemical assay feasibility, (4) Purification feasibility, "
                "(5) Literature novelty. Provide a definitive GO/NO-GO recommendation."
            ),
            "get_controls": (
                "You are an expert medicinal chemist identifying validation compounds. "
                "Generate 10 known positive controls (compounds with measured affinity) "
                "and 10 property-matched negative controls (decoys) for docking validation. "
                "Include PubChem CIDs, SMILES strings, and literature references. "
                "Use DUD-E principles for decoy generation."
            ),
            "chembridge_prep": (
                "You are an expert in computational drug discovery and virtual screening. "
                "Design a pharmacophore-based screening campaign using the ChemBridge Diversity library. "
                "Provide ranked pharmacophore features, physicochemical filters, "
                "PAINS exclusion rules, and ZINC20 query parameters with estimated library sizes."
            ),
            "hit_analysis": (
                "You are an expert in hit prioritization and lead optimization. "
                "Analyze virtual screening hits and prioritize compounds for wet-lab validation. "
                "Provide score cutoff analysis, scaffold clustering, PAINS re-filtering, "
                "selectivity assessment, and a ranked purchase list."
            ),
        }
        return prompts.get(
            task_name,
            "You are an expert computational biochemist assisting drug discovery research."
        )
