"""AI-powered content processing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_optional_current_user
from app.integrations.ai_provider import AIProvider, check_ai_status, get_ai_provider_options
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
    request: dict,
    current_user=Depends(get_optional_current_user)
):
    """Summarize content using AI (Groq/OpenAI/Ollama)."""
    try:
        provider = AIProvider()
        
        title = request.get("title", "")
        content = request.get("content", "")
        category = request.get("category", "tech")
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is required"
            )
        
        result = await provider.summarize(title, content, category)
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
    request: dict,
    current_user=Depends(get_optional_current_user)
):
    """Generate catchy headline using AI."""
    try:
        provider = AIProvider()
        
        title = request.get("title", "")
        content = request.get("content", "")
        
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title is required"
            )
        
        headline = await provider.headline(title, content)
        provider_name = provider.get_provider_name()
        await provider.close()
        
        return SingleResponse(data={
            "headline": headline,
            "original": title,
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
    request: dict,
    current_user=Depends(get_optional_current_user)
):
    """Generate text embedding."""
    try:
        provider = AIProvider()
        
        text = request.get("text", "")
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is required"
            )
        
        embedding = await provider.embed(text)
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
