with open('app/templates/generate_custom.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 594 (index 593) - step2
lines[593] = '                <div class="loading-step" id="step2">{% if pillar_grounding_enabled %}Reviewing relevant threat intelligence...{% else %}Checking authoritative sources...{% endif %}</div>\n'

with open('app/templates/generate_custom.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed step2 line')
