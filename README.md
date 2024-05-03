# streamlit-fastapi-model-serving

# waskrabbeltda

FastAPI and Streamlit setup based on: https://github.com/davidefiocco/streamlit-fastapi-model-serving

To run the application in a machine running Docker and docker compose, run:

    docker compose build
    docker compose up

To visit the FastAPI documentation of the resulting service, visit http://localhost:8000/docs with a web browser.  
To visit the streamlit UI, visit http://localhost:8501.

Logs can be inspected via:

    docker compose logs


### Deployment
- 2 fly instances 
- set secrets with fly secrets
>> fastapi
fly secrets set API_KEY=... g

>> streamlit
fly secrets set API_KEY=... DATA_ENDPOINT=...