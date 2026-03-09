"""AI-powered content processing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_optional_current_user
from app.integrations.ai_provider import AIProvider, check_ai_status, get_ai_provider_options
from app.schemas.content import EmbedRequest, HeadlineRequest, SummarizeRequest
from app.schemas.responses import SingleResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/status",
    summary="Check AI service status",
    description="Returns the current status and availability of configured AI providers (Groq, OpenAI, Ollama).",
    response_model=SingleResponse,
    responses={200: {"description": "AI service status information"}},
)
async def ai_status():
    """Check AI service availability and configuration.

    Reports which AI providers are configured, available, and their current status.
    """
    status_info = await check_ai_status()
    return SingleResponse(data=status_info)


@router.get(
    "/providers",
    summary="List AI providers",
    description="Returns a list of available AI providers and their configuration options.",
    response_model=SingleResponse,
    responses={200: {"description": "List of available AI providers"}},
)
async def list_providers():
    """List available AI providers and their capabilities.

    Returns provider names, supported models, and configuration status.
    """
    options = get_ai_provider_options()
    return SingleResponse(data=options)


@router.post(
    "/summarize",
    summary="Summarize content with AI",
    description="Generates an AI-powered summary of the provided content using the best available provider "
                "(Groq → OpenAI → Ollama). Rate limited to 10 requests per minute.",
    response_model=SingleResponse,
    responses={
        200: {"description": "AI-generated summary"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "No AI provider available"},
    },
)
@limiter.limit("10/minute")
async def summarize_content(
    req: Request,
    request: SummarizeRequest,
    current_user=Depends(get_optional_current_user)
):
    """Summarize content using AI.

    Uses the first available provider (Groq → OpenAI → Ollama) to generate
    a concise summary of the article content.
    """
    try:
        provider = AIProvider()
        
        result = await provider.summarize(request.title, request.content, request.category)
        provider_name = provider.get_provider_name()
        await provider.close()
        
        return SingleResponse(data={
            "summary": result,
            "provider": provider_name,
            "processed_by": current_user.full_name if current_user else "anonymous"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}. Configure GROQ_API_KEY, OPENAI_API_KEY, or start Ollama."
        )


@router.post(
    "/headline",
    summary="Generate headline with AI",
    description="Generates an engaging, catchy headline for the provided content using AI. "
                "Rate limited to 10 requests per minute.",
    response_model=SingleResponse,
    responses={
        200: {"description": "AI-generated headline"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "No AI provider available"},
    },
)
@limiter.limit("10/minute")
async def generate_headline(
    req: Request,
    request: HeadlineRequest,
    current_user=Depends(get_optional_current_user)
):
    """Generate a catchy headline using AI.

    Takes the original title and content, returns an improved, engagement-optimized headline.
    """
    try:
        provider = AIProvider()
        
        headline = await provider.headline(request.title, request.content)
        provider_name = provider.get_provider_name()
        await provider.close()
        
        return SingleResponse(data={
            "headline": headline,
            "original": request.title,
            "provider": provider_name
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}"
        )


@router.post(
    "/embed",
    summary="Generate text embedding",
    description="Generates a vector embedding for the provided text, useful for semantic search and similarity matching. "
                "Rate limited to 10 requests per minute.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Vector embedding with dimensions"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "No AI provider available"},
    },
)
@limiter.limit("10/minute")
async def generate_embedding(
    req: Request,
    request: EmbedRequest,
    current_user=Depends(get_optional_current_user)
):
    """Generate a vector embedding for text.

    Returns a truncated preview (first 10 dimensions) of the embedding
    along with the total dimension count and provider used.
    """
    try:
        provider = AIProvider()
        
        embedding = await provider.embed(request.text)
        provider_name = provider.get_provider_name()
        await provider.close()
        
        return SingleResponse(data={
            "embedding": embedding[:10] + ["..."] if len(embedding) > 10 else embedding,
            "dimensions": len(embedding),
            "provider": provider_name
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}"
        )
