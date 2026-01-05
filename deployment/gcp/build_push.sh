# file should accept version names as args as well as project names
gcloud auth login
# do it all in us-east1  for now
gcloud auth configure-docker us-east1-docker.pkg.dev  # allows domain mapping and rag engine is there

# Build and push the image
docker build -t us-east1-docker.pkg.dev/oicsbx/ocimapped/dev-oicv215-websearch:v2 .
docker push  us-east1-docker.pkg.dev/oicsbx/ocimapped/dev-oicv215-websearch:v2
# convert the other two keys to secrets
gcloud run deploy dev-oicv215-websearch-3 --project oicsbx  --image us-east1-docker.pkg.dev/oicsbx/ocimapped/dev-oicv215-websearch:v1  --platform managed  --region us-east1  --service-account dev-oicv21-cr-sa@oicsbx.iam.gserviceaccount.com  --memory 2Gi  --cpu 2  --timeout 300  --max-instances 3  --min-instances 1  --set-env-vars "GOOGLE_CLOUD_PROJECT=oicsbx,VERTEX_RAG_CORPUS=dev-oic-rakb-rag,GCS_BUCKET_NAME=dev-oicv21-appdata,VERTEX_AI_LOCATION=us-central1,GOOGLE_SEARCH_API_KEY=AIzaSyBxMleN...LcQQH9hJIM,GOOGLE_SEARCH_CSE_ID=b38e...7cd4d86"  --set-secrets "ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,SECRET_KEY=SECRET_KEY:latest"