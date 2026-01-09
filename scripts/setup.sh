# !/bin/bash
# Script to set up and deploy a Cloud Run service from source code
# pick ONE repo to clone (example: hello world)

git clone https://github.com/GoogleCloudPlatform/cloud-run-helloworld-python.git
cd cloud-run-helloworld-python

# set your project (once)
gcloud config set project GCP_PROJECT_ID

# deploy (builds from source using buildpacks or the repo's container config)
gcloud run deploy \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated