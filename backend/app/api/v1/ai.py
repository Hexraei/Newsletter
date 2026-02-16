"""AI-powered content processing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_optional_current_user
from app.integrations.ai_provider import AIProvider, check_ai_status, get_ai_provider_options
from app.schemas.content import EmbedRequest, HeadlineRequest, SummarizeRequest
from app.schemas.responses import SingleResponse

router = APIRouter()


@router.get("/status", response_model=SingleResponse)
async def ai_status():
    """Check AI service status."""
    status_info = await check_ai_status()
    return SingleResponse(data=status_info)


@router.get("/providers", response_model=SingleResponse)
async def list_providers():
    """List available AI providers."""
    options = get_ai_provider_options()
    return SingleResponse(data=options)


@router.post("/summarize", response_model=SingleResponse)
async def summarize_content(
    request: SummarizeRequest,
    current_user=Depends(get_optional_current_user)
):
    """Summarize content using AI (Groq/OpenAI/Ollama)."""
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


@router.post("/headline", response_model=SingleResponse)
async def generate_headline(
    request: HeadlineRequest,
    current_user=Depends(get_optional_current_user)
):
    """Generate catchy headline using AI."""
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


@router.post("/embed", response_model=SingleResponse)
async def generate_embedding(
    request: EmbedRequest,
    current_user=Depends(get_optional_current_user)
):
    """Generate text embedding."""
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
