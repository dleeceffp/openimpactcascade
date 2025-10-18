import os
import json
import argparse
import google.generativeai as genai

def generate_questions(context: str, api_key: str):
    """Generates questions using the Gemini API."""
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""\
    You are an expert Enterprise Security Risk Management (ESRM) consultant. Your task is to generate a series of 3 to 5 questions to help an organization assess a specific risk scenario based on the FAIR model. The questions should be in a specific JSON format. The first question should always be a PERT estimate for 'Loss Event Frequency (LEF)', and the second should be a PERT estimate for 'Loss Magnitude (LM)'. Subsequent questions can be multiple choice to refine the scenario.\
\
    Based on the following context, please generate a JSON object containing 3 to 5 questions for a risk analysis. The final question's `next_question_id` must be null.\
\
    Context: "{context}"\
\
    JSON Format Requirements:\
    1. The root of the JSON object must have two keys: `start_question_id` and `questions`.\
    2. `start_question_id` must be "q1".\
    3. `questions` is an object where each key is a question ID (e.g., "q1", "q2").\
    4. Each question object must have `text` (string), `type` (string), and `next_question_id` (string or null).\
    5. For `pert_estimate` questions, you must also include a `name` key, with a value of either "lef" or "lm".\
    6. For `multiple_choice` questions, you must include a `choices` key, which is an array of objects, each with `text` and `next_question_id`.\
    7. The first question (q1) must be of type `pert_estimate` with the name `lef`.\
    8. The second question (q2) must be of type `pert_estimate` with the name `lm`.\
    9. The `next_question_id` of the last question must be null.\
\
    Provide only the raw JSON object as the output.\
    """

    try:
        response = model.generate_content(prompt)
        # Clean the response to get raw JSON
        json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(json_string)
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Raw response from API: {response.text if 'response' in locals() else 'No response'}")
        return None

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Generate risk analysis questions using Gemini.')
    parser.add_argument('context', type=str, help='The organizational context for generating questions.')
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return

    print("Generating questions with Gemini...")
    generated_json = generate_questions(args.context, api_key)

    if generated_json:
        print("\n--- Generated Questions ---")
        print(json.dumps(generated_json, indent=2))
        print("\n-------------------------")

if __name__ == "__main__":
    main()
