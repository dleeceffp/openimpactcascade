import sys
import re

with open('app/templates/generate.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix step4 line - remove emoji
content = re.sub(
    r'<div class="loading-step" id="step4">\{% if pillar_grounding_enabled %\}[^<]+\{% else %\}[^<]+\{% endif %\}</div>',
    '<div class="loading-step" id="step4">{% if pillar_grounding_enabled %}Building scenario-focused questions...{% else %}Preparing the assessment...{% endif %}</div>',
    content
)

with open('app/templates/generate.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed generate.html')
