"""Quick check of AI provider status."""

from app.integrations.ai_provider import AIProvider, get_ai_provider_options

# Check what provider will be used
options = get_ai_provider_options()
print('='*60)
print('AI PROVIDER OPTIONS')
print('='*60)

for p in options['providers']:
    status = '[OK]' if p['status'] in ['configured', 'always_available'] else '[  ]'
    print(f'  {status} {p["name"]}: {p["cost"]}')

print()
print(f'Active provider: {options["active"]}')
print(f'Recommendation: {options["recommendation"]}')
print('='*60)
