# AI Job Applicant Bot - GitHub Codespaces Guide

This guide explains how to open and work with the repository in GitHub Codespaces.

## Launching a Codespace

1. Navigate to the repository on GitHub.
2. Click the **Code** button and choose **Open with Codespaces**.
3. Create a new Codespace or select an existing one.

## Dev Container Configuration

The repository contains a `.devcontainer` directory with a `devcontainer.json` file:

```json
{
  "name": "AI Job Applicant Bot",
  "image": "mcr.microsoft.com/devcontainers/python:0-3.10",
  "postCreateCommand": "pip install -r requirements.txt",
  "forwardPorts": [8501]
}
```

This configuration installs required Python dependencies and forwards port **8501** so the Streamlit UI can run in the Codespace.

## Running the Streamlit UI

Once your Codespace is ready, launch the app from the terminal:

```bash
streamlit run ui/app.py
```

GitHub Codespaces will automatically forward port 8501, allowing you to open the Streamlit interface in your browser.
