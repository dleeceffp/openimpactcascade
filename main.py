import os
import json
from flask import Flask, render_template, request, redirect, url_for

from simulation import run_monte_carlo

app = Flask(__name__)

@app.route('/')
def home():
    """Renders the home page with the questionnaire."""
    with open('questions.json', 'r') as f:
        questions = json.load(f)
    return render_template('index.html', questions=questions)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Processes the risk analysis form and displays the results."""
    if request.method == 'POST':
        try:
            # Store original inputs for recalculation
            original_inputs = {
                'lef_min': float(request.form.get('lef_min')),
                'lef_mle': float(request.form.get('lef_mle')),
                'lef_max': float(request.form.get('lef_max')),
                'lm_min': float(request.form.get('lm_min')),
                'lm_mle': float(request.form.get('lm_mle')),
                'lm_max': float(request.form.get('lm_max'))
            }
            n_simulations = int(request.form.get('n_simulations', 10000))

            # Run the initial simulation
            results = run_monte_carlo(**original_inputs, n_simulations=n_simulations)
            
            return render_template('results.html', results=results, original_inputs=original_inputs, n_simulations=n_simulations)
        except (ValueError, TypeError):
            # A simple error handler for invalid number inputs
            return "Invalid input. Please ensure all fields are numbers.", 400

    # Redirect home if accessed via GET
    return redirect(url_for('home'))

@app.route('/recalculate', methods=['POST'])
def recalculate():
    """Recalculates the simulation with adjusted parameters and returns JSON."""
    data = request.get_json()
    
    # Get original inputs and reduction percentages
    inputs = data.get('original_inputs')
    likelihood_reduction = data.get('likelihood_reduction', 0) / 100.0
    impact_reduction = data.get('impact_reduction', 0) / 100.0
    n_simulations = data.get('n_simulations', 10000)

    # Apply reductions
    adjusted_inputs = {
        'lef_min': inputs['lef_min'] * (1 - likelihood_reduction),
        'lef_mle': inputs['lef_mle'] * (1 - likelihood_reduction),
        'lef_max': inputs['lef_max'] * (1 - likelihood_reduction),
        'lm_min': inputs['lm_min'] * (1 - impact_reduction),
        'lm_mle': inputs['lm_mle'] * (1 - impact_reduction),
        'lm_max': inputs['lm_max'] * (1 - impact_reduction)
    }

    # Run new simulation
    new_results = run_monte_carlo(**adjusted_inputs, n_simulations=n_simulations)
    return new_results

if __name__ == "__main__":
    # This is used when running locally. Gunicorn is used when deploying.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
