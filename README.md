# OpenImpactCascade

This project is a web application for quantitative risk analysis based on the FAIR (Factor Analysis of Information Risk) methodology and ESRM (Enterprise Security Risk Management) principles.

## Features

*   Accepts risk inputs via a dynamic, tree-structured questionnaire.
*   Allows manipulation of control variables (e.g., reducing impact or likelihood) to see the effect on residual risk.
*   Performs Monte Carlo simulations to model risk distributions.
*   Generates visualizations of risk analysis results for business leaders.

## Tech Stack

*   **Backend:** Python (Flask)
*   **Frontend:** HTML, CSS, JavaScript (with Chart.js)
*   **Database:** SQLite (for development)
*   **Deployment:** Docker, Google Cloud Run

## Running with Docker Locally

1.  **Build the Docker image:**
    From the root directory of the project, run:
    ```bash
    docker build -t open-impact-cascade .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8080:8080 open-impact-cascade
    ```

3.  **Access the application:**
    Open your web browser and navigate to `http://localhost:8080`.

## Deployment to Google Cloud Run

These instructions assume you have the `gcloud` CLI installed and configured.

1.  **Set your Project ID:**
    ```bash
    export PROJECT_ID="your-gcp-project-id"
    gcloud config set project $PROJECT_ID
    ```

2.  **Enable required APIs:**
    ```bash
    gcloud services enable run.googleapis.com
    gcloud services enable artifactregistry.googleapis.com
    gcloud services enable cloudbuild.googleapis.com
    ```

3.  **Build the container image using Cloud Build:**
    ```bash
    gcloud builds submit --tag gcr.io/$PROJECT_ID/open-impact-cascade
    ```

4.  **Deploy to Cloud Run:**
    ```bash
    gcloud run deploy open-impact-cascade \
      --image gcr.io/$PROJECT_ID/open-impact-cascade \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated
    ```
    Replace `us-central1` with your preferred region. After deployment, `gcloud` will provide you with the URL to access your application.
