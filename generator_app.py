import os
from flask import Flask, render_template, request, jsonify, Response
from ai_question_generator import AIQuestionGenerator

app = Flask(__name__)

# Check for API key at startup
api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY environment variable not set. Please set it before running the app.")

# Initialize the generator once to be reused across requests
try:
    generator = AIQuestionGenerator(api_key=api_key)
    print("AIQuestionGenerator initialized successfully.")
except Exception as e:
    raise RuntimeError(f"Failed to initialize AIQuestionGenerator: {e}")

@app.route('/')
def index():
    """Renders the main input page."""
    # Data for dropdowns, taken from the original script
    industries = [
        "Healthcare", "Financial Services", "Retail/E-commerce",
        "Construction", "Manufacturing", "Technology/Software",
        "Education", "Legal Services", "Energy/Utilities",
        "Transportation/Logistics", "Hospitality", "Real Estate"
    ]
    regions = [
        "Canada", "United States", "United Kingdom", "European Union",
        "Australia", "Japan", "Singapore", "India", "Brazil", "Mexico"
    ]
    return render_template('index.html', industries=industries, regions=regions)

@app.route('/generate', methods=['POST'])
def generate():
    """Handles the questionnaire generation request."""
    try:
        industry = request.form.get('industry')
        region = request.form.get('region')
        org_size = request.form.get('organization_size')

        if not industry or not region:
            return jsonify({"error": "Industry and Region are required."}), 400

        print(f"Generating questionnaire for Industry: {industry}, Region: {region}, Size: {org_size}")

        questionnaire = generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None
        )
        
        # Return the generated questionnaire as a JSON file download
        safe_industry = industry.replace("/", "-").replace(" ", "_")
        safe_region = region.replace("/", "-").replace(" ", "_")
        filename = f"questions_{safe_industry}_{safe_region}.json"

        return Response(
            jsonify(questionnaire).get_data(as_text=True),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )

    except Exception as e:
        print(f"An error occurred during generation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to generate questionnaire.", "details": str(e)}), 500

if __name__ == '__main__':
    # Note: Use a production-ready WSGI server like Gunicorn or Waitress for deployment
    app.run(debug=True, port=5001)
