import re

with open('app/templates/generate_custom.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update title
content = content.replace(
    '<title>Custom Risk Scenario - OpenImpactCascade</title>',
    '<title>Assess Specific Risk - OpenImpactCascade</title>'
)

# 2. Update page heading and add Lucide icon styling (add before </style>)
icon_styles = '''
        /* Lucide icon styling */
        .icon {
            display: inline-block;
            vertical-align: middle;
            width: 20px;
            height: 20px;
            stroke: currentColor;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
            fill: none;
            margin-right: 8px;
        }

        .page-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }

        .page-header .icon {
            width: 28px;
            height: 28px;
            color: #4a5568;
        }

        .panel-icon {
            color: #4a5568;
        }
'''

# Insert icon styles before </style>
content = content.replace('</style>', icon_styles + '    </style>')

# 3. Replace heading section
old_heading = '''<a href="{{ url_for('home') }}" class="back-link">← Back to Home</a>
        
        <h1>🎯 Custom Risk Scenario Assessment</h1>
        <p class="subtitle">
            Define your specific risk scenario and we'll create a tailored questionnaire focused on that exact threat, grounded in authoritative research.
        </p>'''

new_heading = '''<a href="{{ url_for('home') }}" class="back-link"><i data-lucide="arrow-left" class="icon" style="width: 16px; height: 16px;"></i>Back to Home</a>

        <div class="page-header">
            <i data-lucide="clipboard-check" class="icon"></i>
            <h1>Assess a Specific Risk Scenario</h1>
        </div>
        <p class="subtitle">
            Define your specific risk scenario to generate a tailored assessment focused on that exact threat, grounded in authoritative research.
        </p>'''

content = content.replace(old_heading, new_heading)

# 4. Update info box - How This Works
old_info = '''<div class="info-box">
            <strong>🎯 How This Works:</strong>
            <ul>
                <li>You define the specific risk scenario you want to assess</li>
                <li>AI researches that exact threat using MITRE ATT&CK and relevant industry sources</li>
                <li>Questions are tailored to your specific scenario, not generic threats</li>
                <li>Get scenario-specific frequency and impact estimates</li>
            </ul>
        </div>'''

new_info = '''<div class="info-box">
            <strong>How This Works</strong>
            <ul>
                <li>You define the specific risk scenario you want to assess</li>
                <li>Research on that exact threat using MITRE ATT&CK and relevant industry sources</li>
                <li>Questions are tailored to your specific scenario, not generic threats</li>
                <li>Get scenario-specific frequency and impact estimates</li>
            </ul>
        </div>'''

content = content.replace(old_info, new_info)

# 5. Update Industry Likelihood Grounding panel
old_likelihood = '''<div class="info-box" style="background: #f0f9ff; border-left-color: #0284c7;">
            <strong>📈 Industry Likelihood Grounding:</strong>
            <p style="margin: 5px 0 0 0; font-size: 0.9em;">
                Verizon DBIR {{ dbir_edition or 'latest' }} breach statistics will be used to inform
                threat likelihood estimates specific to your selected industry.
            </p>
        </div>'''

new_likelihood = '''<div class="info-box" style="background: #f0f9ff; border-left-color: #0284c7;">
            <strong><i data-lucide="bar-chart-3" class="icon panel-icon"></i>Industry Risk Baseline</strong>
            <p style="margin: 5px 0 0 0; font-size: 0.9em;">
                Verizon DBIR {{ dbir_edition or 'latest' }} industry statistics will help establish an initial likelihood baseline for the selected sector. You can refine assumptions during the assessment.
            </p>
        </div>'''

content = content.replace(old_likelihood, new_likelihood)

# 6. Update Tips heading
content = content.replace(
    '<h3>💡 Tips for describing your concern:</h3>',
    '<h3>Tips for describing your concern:</h3>'
)

# 7. Update refine button
content = content.replace(
    '<button type="button" class="btn-refine" id="refineBtn" onclick="refineScenario()">\n                    ✨ Help Me Refine This Into a Clear Scenario\n                </button>',
    '<button type="button" class="btn-refine" id="refineBtn" onclick="refineScenario()">\n                    Help Me Refine This Into a Clear Scenario\n                </button>'
)

# 8. Update loading title
content = content.replace(
    '<p><strong>Researching your specific scenario...</strong></p>',
    '<p><strong>Preparing your risk assessment...</strong></p>'
)

# 9. Update loading steps - remove all emoji
content = re.sub(
    r'{% if pillar_grounding_enabled %}[^<]+Loading industry likelihood data[^<]+\{% else %\}[^<]+\{% endif %\}',
    '{% if pillar_grounding_enabled %}Loading industry risk baseline...{% else %}Reviewing relevant threat intelligence...{% endif %}',
    content
)

# Fix specific loading step lines
content = content.replace(
    '{% if pillar_grounding_enabled %} Loading industry likelihood data (DBIR {{ dbir_edition or \'latest\' }})...{% else %} Searching for scenario-specific threat intelligence...{% endif %}',
    '{% if pillar_grounding_enabled %}Loading industry risk baseline...{% else %}Reviewing relevant threat intelligence...{% endif %}'
)

content = content.replace(
    '{% if pillar_grounding_enabled %} Searching for scenario-specific threat intelligence...{% else %} Verifying documented incidents and sources...{% endif %}',
    '{% if pillar_grounding_enabled %}Reviewing relevant threat intelligence...{% else %}Checking authoritative sources...{% endif %}'
)

content = content.replace(
    '{% if pillar_grounding_enabled %}📋 Verifying documented incidents and sources...{% else %}🎯 Building scenario-tailored questions...{% endif %}',
    '{% if pillar_grounding_enabled %}Checking authoritative sources...{% else %}Building scenario-focused questions...{% endif %}'
)

content = content.replace(
    '{% if pillar_grounding_enabled %}🎯 Building scenario-tailored questions...{% else %}✅ Finalizing custom assessment...{% endif %}',
    '{% if pillar_grounding_enabled %}Building scenario-focused questions...{% else %}Preparing the assessment...{% endif %}'
)

content = content.replace(
    '{% if pillar_grounding_enabled %}<div class="loading-step" id="step5">✅ Finalizing custom assessment...</div>{% endif %}',
    '{% if pillar_grounding_enabled %}<div class="loading-step" id="step5">Preparing the assessment...</div>{% endif %}'
)

# 10. Update Generate Assessment button
content = content.replace(
    '<button type="submit" class="btn-primary" id="submitBtn">\n                    Generate Assessment 🎯\n                </button>',
    '<button type="submit" class="btn-primary" id="submitBtn">\n                    Prepare Assessment\n                </button>'
)

# 11. Update chat welcome message
content = content.replace(
    '"welcome_message": "👋 Hi! I am here to help you define your custom risk scenario. I can help you:<ul style=\\"margin: 10px 0 0 20px; font-size: 0.95em;\\"><li>Clarify your risk concerns</li><li>Identify relevant threat actors</li><li>Understand FAIR methodology</li><li>Refine your scenario description</li></ul>Feel free to ask any questions!",',
    '"welcome_message": "Welcome! I\'m here to help you define your custom risk scenario. I can help you:<ul style=\\"margin: 10px 0 0 20px; font-size: 0.95em;\\"><li>Clarify your risk concerns</li><li>Identify relevant threat actors</li><li>Understand FAIR methodology</li><li>Refine your scenario description</li></ul>Feel free to ask any questions!",'
)

# 12. Update quick help buttons
content = content.replace(
    '{"text": "📝 Good Scenario Tips", "question": "What makes a good risk scenario?"}',
    '{"text": "Good Scenario Tips", "question": "What makes a good risk scenario?"}'
)
content = content.replace(
    '{"text": "💡 Describe Concern", "question": "How should I describe my concern?"}',
    '{"text": "Describe Concern", "question": "How should I describe my concern?"}'
)
content = content.replace(
    '{"text": "📊 About FAIR", "question": "What is FAIR methodology?"}',
    '{"text": "About FAIR", "question": "What is FAIR methodology?"}'
)

# 13. Update analyzing button text
content = content.replace(
    "refineBtn.textContent = '🔄 Analyzing your concern...';",
    "refineBtn.textContent = 'Analyzing your concern...';"
)

# 14. Update key concerns heading
content = content.replace(
    "<h4>🎯 Key Concerns Identified:</h4>",
    "<h4>Key Concerns Identified:</h4>"
)

# 15. Add Lucide script before closing body
if 'lucide.createIcons()' not in content:
    content = content.replace(
        '</body>',
        '    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>\n    <script>lucide.createIcons();</script>\n</body>'
    )

with open('app/templates/generate_custom.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated generate_custom.html')
