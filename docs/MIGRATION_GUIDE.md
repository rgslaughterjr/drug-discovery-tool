# Migration Guide: Anthropic-Only → Multi-Provider

If you were using the previous **Anthropic-only** version of the Drug Discovery Pipeline, here's what changed and what you need to know.

---

## TL;DR (Key Changes)

| Aspect | Old | New |
|--------|-----|-----|
| **Provider Support** | Anthropic + Bedrock only | 7 providers: Anthropic, OpenAI, Cohere, Ollama, Together, Bedrock, + custom APIs |
| **Configuration** | `provider: Literal["anthropic", "bedrock"]` | `provider: str` (any provider name) |
| **Base URL** | Not supported | Supported (for custom endpoints, Azure OpenAI, Ollama) |
| **Client Init** | `DrugDiscoveryClient(config)` | Same, but supports all providers |
| **Notebooks** | Manual Anthropic setup | Interactive setup cell (any provider) |
| **README** | Anthropic/Bedrock focused | Multi-provider guide with cost comparisons |

**Backward compatibility:** ✓ Yes. All old code using Anthropic still works unchanged.

---

## What's Compatible (No Code Changes Needed)

If you were using Anthropic, your existing code is 100% compatible:

```python
# OLD CODE (still works)
from src import DrugDiscoveryClient, APIConfig

config = APIConfig(
    provider="anthropic",
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022"
)
client = DrugDiscoveryClient(config=config)

result = client.evaluate_target(
    organism="Staphylococcus aureus",
    protein_name="DNA gyrase subunit B"
)
```

✓ This runs unchanged with the new code.

---

## What Changed (For New Users or Switching Providers)

### 1. APIConfig now accepts any provider

**Old:**
```python
config = APIConfig(
    provider: Literal["anthropic", "bedrock"]  # Only these two
)
```

**New:**
```python
config = APIConfig(
    provider: str  # Any string: "anthropic", "openai", "cohere", "ollama", etc.
)
```

### 2. New optional parameter: `base_url`

For OpenAI-compatible APIs (including Azure OpenAI, Ollama, custom endpoints):

```python
# Old: Not possible
# New: Now supported for Ollama
config = APIConfig(
    provider="ollama",
    model="llama2",
    base_url="http://localhost:11434/v1"
)

# New: Azure OpenAI
config = APIConfig(
    provider="openai",
    model="gpt-4",
    api_key="your-azure-key",
    base_url="https://YOUR_RESOURCE.openai.azure.com/v1"
)
```

### 3. Environment variable flexibility

**Old:** Only `ANTHROPIC_API_KEY`, `DISCOVERY_PROVIDER` (anthropic/bedrock)

**New:** Smart API key detection

```python
# Old setup
export ANTHROPIC_API_KEY="sk-ant-..."
export DISCOVERY_PROVIDER="anthropic"

# New setup (same as above, still works)
# But now also supports:
export DISCOVERY_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."

# Or generic:
export DISCOVERY_API_KEY="..."  # Auto-detected for any provider
```

### 4. Jupyter notebooks: New interactive setup cell

**Old:** Manually set `ANTHROPIC_API_KEY` environment variable before running notebook

**New:** Integrated setup cell in every notebook
```
1. SELECT YOUR LLM PROVIDER (interactive menu)
2. AUTHENTICATE (masked key input)
3. SELECT MODEL (with defaults)
4. OPTIONAL: CUSTOM ENDPOINT
5. TESTING CONNECTION
```

Notebooks now work immediately without pre-configuration.

---

## Upgrading Your Installation

### If you're using Anthropic (no changes to code)

```bash
# Update the package (if using git)
git pull origin main

# Install dependencies (includes new optional packages)
pip install -r requirements.txt

# Your old code runs unchanged
python your_script.py  # Still works
jupyter notebook workflows/01_evaluate_target.ipynb  # Still works
```

### If you want to switch to a new provider

```bash
# Install provider-specific dependencies
pip install openai  # For OpenAI
pip install cohere  # For Cohere
pip install ollama  # For Ollama (optional; uses openai package)

# Update your code (one line change)
config = APIConfig(
    provider="openai",  # Changed from "anthropic"
    api_key="sk-...",   # Your OpenAI key
    model="gpt-4-turbo"
)
```

---

## Detailed Code Migration Examples

### Example 1: Anthropic → OpenAI

**Old code:**
```python
from src import DrugDiscoveryClient, APIConfig

config = APIConfig(
    provider="anthropic",
    api_key="sk-ant-YOUR_KEY",
    model="claude-3-5-sonnet-20241022"
)
client = DrugDiscoveryClient(config=config)

result = client.evaluate_target(
    organism="Staphylococcus aureus",
    protein_name="DNA gyrase subunit B"
)
```

**New code (switching to OpenAI):**
```python
from src import DrugDiscoveryClient, APIConfig

config = APIConfig(
    provider="openai",  # Changed
    api_key="sk-YOUR_OPENAI_KEY",  # Changed
    model="gpt-4-turbo"  # Changed (optional; can use gpt-4 or gpt-3.5-turbo)
)
client = DrugDiscoveryClient(config=config)

# Everything else unchanged
result = client.evaluate_target(
    organism="Staphylococcus aureus",
    protein_name="DNA gyrase subunit B"
)
```

### Example 2: Anthropic → Local Ollama

**Old code:**
```python
config = APIConfig(
    provider="anthropic",
    api_key="sk-ant-YOUR_KEY",
)
```

**New code (switching to free local Ollama):**
```python
config = APIConfig(
    provider="ollama",  # Changed
    # api_key not needed for Ollama
    model="llama2",  # Changed
    base_url="http://localhost:11434/v1"  # New
)
# First, run: ollama serve in another terminal
# Then: ollama pull llama2
```

### Example 3: Anthropic → Azure OpenAI

**Old code:**
```python
config = APIConfig(
    provider="anthropic",
    api_key="sk-ant-YOUR_KEY",
)
```

**New code (switching to Azure OpenAI):**
```python
config = APIConfig(
    provider="openai",  # Changed (Azure uses OpenAI protocol)
    api_key="YOUR_AZURE_API_KEY",  # Changed to Azure key
    model="gpt-4",  # Your deployed model name on Azure
    base_url="https://YOUR_RESOURCE.openai.azure.com/v1"  # New: Azure endpoint
)
```

---

## Logging & Debugging

### Check which provider is active

```python
client = DrugDiscoveryClient(config)
print(f"Provider: {client.config.provider}")
print(f"Model: {client.model_id}")
print(f"Provider type: {client.provider_type}")
```

### Common provider-specific properties

```python
# For Anthropic and Bedrock (native API objects)
client.client  # The Anthropic or boto3 client

# For OpenAI-compatible (OpenAI, Ollama, Together, etc.)
client.client  # The OpenAI client

# For Cohere
client.client  # The Cohere client
```

---

## Provider Performance & Cost (Quick Reference)

Per full pipeline execution (all 4 workflows):

| Provider | Cost | Quality | Setup Time | Local |
|----------|------|---------|------------|-------|
| Anthropic | $0.35 | Excellent | 2 min | No |
| OpenAI (GPT-4) | $1.50 | Excellent | 2 min | No |
| OpenAI (GPT-3.5) | $0.50 | Good | 2 min | No |
| Cohere | $0.50 | Good | 2 min | No |
| Ollama | Free | Decent | 10 min | **Yes** |
| Together.ai | $0.80 | Good | 2 min | No |
| Bedrock | $0.40 | Excellent | 5 min | No |

---

## Environment Variable Mapping

### Old (Anthropic-only)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DISCOVERY_PROVIDER="anthropic"  # or "bedrock"
export DISCOVERY_MODEL="claude-3-5-sonnet-20241022"
export AWS_REGION="us-west-2"  # For Bedrock only
```

### New (Any provider)

```bash
# Generic (auto-detected)
export DISCOVERY_PROVIDER="anthropic"  # or "openai", "cohere", "ollama", etc.
export DISCOVERY_API_KEY="..."  # Smart detection based on provider
export DISCOVERY_MODEL="..."    # Provider-specific model name
export DISCOVERY_BASE_URL="..."  # For custom endpoints (Ollama, Azure, etc.)

# Or provider-specific
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export COHERE_API_KEY="..."
export TOGETHER_API_KEY="..."
export AWS_REGION="us-west-2"  # For Bedrock
```

---

## Testing Your Migration

### Verify old Anthropic code still works

```bash
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY"

# Run your old script (should work unchanged)
python my_old_script.py
```

### Try a new provider

```bash
# Switch provider
export DISCOVERY_PROVIDER="openai"
export OPENAI_API_KEY="sk-YOUR_KEY"

# Run a notebook
jupyter notebook workflows/01_evaluate_target.ipynb
# Select "openai" in the setup cell
```

---

## FAQ

**Q: Will my old Anthropic code break?**
A: No. All old code is 100% backward compatible.

**Q: Do I have to migrate to a new provider?**
A: No. Anthropic works exactly as before.

**Q: Can I use multiple providers in the same notebook?**
A: Yes. Create multiple `DrugDiscoveryClient` instances with different configs.

**Q: What if my provider isn't listed?**
A: If it's OpenAI-compatible, use `provider="custom"` and set `base_url` and `api_key`.

**Q: How do I report issues with a specific provider?**
A: Open a GitHub issue with the provider name and error message.

**Q: Can I use local LLMs (Ollama) for free?**
A: Yes! Ollama is completely free and runs locally. See setup guide in README_MULTIprovider.md.

---

## Need Help?

- **For provider-specific setup:** See `README_MULTIprovider.md`
- **For troubleshooting:** Check the Troubleshooting section in README_MULTIprovider.md
- **For API reference:** See README_MULTIprovider.md > API Reference
- **For GitHub issues:** Report with provider name, error message, and steps to reproduce

---

## Summary of Benefits

✓ **No lock-in:** Use any LLM provider you have access to
✓ **Cost optimization:** Compare prices across providers easily
✓ **Local option:** Run offline with Ollama
✓ **Backward compatible:** Old code works unchanged
✓ **Easy setup:** Interactive notebook cells guide you
✓ **Consistent API:** Same code works for all providers

Welcome to the provider-agnostic future of the Drug Discovery Pipeline!
