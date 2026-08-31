"""Pydantic models for OpenRouter free models data."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ModelPricing(BaseModel):
    """Pricing information for a model."""
    prompt: str
    completion: str
    request: str = "0"
    image: str = "0"


class ModelArchitecture(BaseModel):
    """Model architecture information."""
    modality: str
    input_modalities: list[str]
    output_modalities: list[str]
    tokenizer: str
    instruct_type: str | None = None


class AABenchmarkEntry(BaseModel):
    """Artificial Analysis benchmark entry."""
    agentic_index: float | None = None
    coding_index: float | None = None
    intelligence_index: float | None = None


class DABenchmarkEntry(BaseModel):
    """Design Arena benchmark entry."""
    arena: str
    category: str
    elo: float
    rank: int
    win_rate: float


class ModelBenchmarks(BaseModel):
    """Third-party benchmark rankings for a model."""
    artificial_analysis: AABenchmarkEntry | None = None
    design_arena: list[DABenchmarkEntry] = []


class ModelReasoning(BaseModel):
    """Reasoning effort configuration."""
    mandatory: bool = False
    default_enabled: bool = False
    supported_efforts: list[str] = []
    default_effort: str | None = None
    supports_max_tokens: bool = False


class TopProviderInfo(BaseModel):
    """Information about the top provider for a model."""
    context_length: int | None = None
    is_moderated: bool
    max_completion_tokens: int | None = None


class ModelLinks(BaseModel):
    """Related API endpoints and resources for a model."""
    details: str


class FreeModel(BaseModel):
    """Free model data from OpenRouter API."""
    id: str
    canonical_slug: str
    name: str
    created: int | str = 0
    description: str
    context_length: int
    architecture: ModelArchitecture
    pricing: ModelPricing
    top_provider: TopProviderInfo
    benchmarks: ModelBenchmarks | None = None
    reasoning: ModelReasoning | None = None
    expiration_date: str | None = None
    knowledge_cutoff: str | None = None
    hugging_face_id: str | None = None
    links: ModelLinks | None = None
    alias_target: dict | None = None
    default_parameters: dict | None = None
    supported_parameters: list[str] = []
    supported_voices: list[str] | None = None
    per_request_limits: dict | None = None

    release_date: datetime = Field(default_factory=lambda: datetime.fromtimestamp(0, tz=UTC))
    coding_index: float | None = None
    intelligence_index: float | None = None
    is_expired: bool = False
    modalities_badges: list[str] = []
    rank: int = 0

    def model_post_init(self, __context, /) -> None:
        """Compute derived fields after initialization."""
        self.release_date = parse_slug_date(self.canonical_slug)
        
        if self.benchmarks and self.benchmarks.artificial_analysis:
            self.coding_index = self.benchmarks.artificial_analysis.coding_index
            self.intelligence_index = self.benchmarks.artificial_analysis.intelligence_index
        
        self.is_expired = is_expired(self.expiration_date)
        self.modalities_badges = get_modality_badges(self.architecture.input_modalities)


MODALITY_ICONS = {
    "text": "📝 Text",
    "image": "🖼️ Image",
    "video": "🎥 Video",
    "audio": "🔊 Audio",
    "file": "📎 File",
}


def get_modality_badges(input_modalities: list[str]) -> list[str]:
    """Convert input modalities to display badges."""
    return [MODALITY_ICONS.get(m, m) for m in input_modalities]


def parse_slug_date(canonical_slug: str) -> datetime:
    """Extract YYYYMMDD from slug like 'org/model-20260616'."""
    import re
    match = re.search(r'-(\d{8})$', canonical_slug)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.fromtimestamp(0, tz=UTC)


def is_expired(expiration_date: str | None) -> bool:
    """Check if model has expired."""
    if not expiration_date:
        return False
    try:
        exp = datetime.strptime(expiration_date, "%Y-%m-%d").replace(tzinfo=UTC)
        return exp < datetime.now(UTC)
    except ValueError:
        return False


def humanize_tokens(n: int) -> str:
    """Convert token count to human-readable string."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".rstrip('0').rstrip('.')
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".rstrip('0').rstrip('.')
    return str(n)


def coding_index_color(coding_index: float | None) -> str:
    """Get CSS color class for coding index."""
    if coding_index is None:
        return "na"
    if coding_index >= 60:
        return "high"
    if coding_index >= 40:
        return "medium"
    return "low"


def reasoning_summary(reasoning: ModelReasoning | None) -> str:
    """Generate a brief summary of reasoning capabilities."""
    if not reasoning:
        return "Not specified"
    parts = []
    if reasoning.mandatory:
        parts.append("Mandatory")
    elif reasoning.default_enabled:
        parts.append("Enabled by default")
    else:
        parts.append("Optional")
    if reasoning.supported_efforts:
        efforts = ", ".join(reasoning.supported_efforts)
        parts.append(f"Efforts: {efforts}")
    return "; ".join(parts)