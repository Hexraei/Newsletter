"""AI System Diagnostics Test"""

import asyncio
import sys

print('='*60)
print('AI SYSTEM DIAGNOSTICS')
print('='*60)

# Test backend AI integration
print('\n[Step 1] Checking AI configuration...')

try:
    from app.integrations.ai_provider import AIProvider, check_ai_status
    
    # Create provider - it will auto-select free option
    provider = AIProvider()
    print('[OK] AI Provider initialized')
    print('[INFO] Using: ' + provider.get_provider_name())
    
except Exception as e:
    print('[FAIL] Could not initialize AI provider: ' + str(e))
    sys.exit(1)

# Test the provider
print('\n[Step 2] Testing AI connection...')

try:
    async def test_ai():
        # Check status
        status = await check_ai_status()
        print('[INFO] Status: ' + status["status"])
        print('[INFO] Provider: ' + status.get("provider", "Unknown"))
        
        # Test generation
        print('\n[Step 3] Testing content generation...')
        
        result = await provider.summarize(
            title="Test: AI News",
            content="Artificial intelligence is transforming how we work and learn.",
            category="tech"
        )
        
        print('[OK] Summary generated successfully!')
        print('[INFO] Generated ' + str(len(result.get("key_points", []))) + ' key points')
        
        await provider.close()
        return True
    
    success = asyncio.run(test_ai())
    
    if not success:
        sys.exit(1)
        
except Exception as e:
    print('[FAIL] AI test error: ' + str(e))
    sys.exit(1)

print('')
print('='*60)
print('SUCCESS! AI SYSTEM IS WORKING')
print('='*60)
print('')
print('You can now use AI features without any signup!')
print('Provider: Pollinations AI (Free)')
print('')
