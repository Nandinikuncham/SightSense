# SightSense — AI Scene Description & Hazard Alert for the Visually Impaired

<p align="center">
  <strong>See the surroundings. Understand the scene. Move with greater awareness.</strong>
</p>

<p align="center">
  An assistive technology project designed to help visually impaired users understand their surroundings through scene descriptions, prioritized information, and hazard alerts.
</p>

<p align="center">
  <a href="https://github.com/YOUR_USERNAME/SightSense">
    <img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github" alt="GitHub Repository">
  </a>
  <a href="YOUR_DEMO_VIDEO_URL">
    <img src="https://img.shields.io/badge/Watch-Demo%20Video-red?style=for-the-badge&logo=youtube" alt="Demo Video">
  </a>
  <a href="YOUR_DOCUMENTATION_URL">
    <img src="https://img.shields.io/badge/Read-Documentation-blue?style=for-the-badge&logo=readthedocs" alt="Documentation">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-See%20File-lightgrey?style=for-the-badge" alt="License">
  </a>
</p>


##  Overview

SightSense is an assistive technology project focused on helping visually impaired people better understand their surroundings.

The application is designed to process an image captured by a user and present relevant scene information in an accessible format. Instead of simply listing everything visible in an image, SightSense aims to prioritize information that may matter to the user, such as nearby people, objects, and potential obstacles.

The system combines a web-based interface, a backend API, scene-analysis components, and text-to-speech capabilities.

### Our Vision

To make environmental information more accessible through clear, timely, and understandable descriptions that can support users as they navigate everyday environments.

> SightSense is an assistive information tool and is not a replacement for a white cane, guide dog, trained mobility support, or other established mobility aids.

---

##  Problem Statement

Visually impaired people may face difficulties understanding unfamiliar or changing environments, including:

* Identifying objects and people in their surroundings.
* Understanding the arrangement of objects in a scene.
* Noticing potential obstacles along a path.
* Accessing visual environmental information independently.
* Receiving useful information without having to interpret a long list of detected objects.

Many image-description systems focus on describing what is visible, but accessibility scenarios can also require information to be concise, relevant, and presented in an understandable order.

SightSense explores how scene descriptions and spoken feedback can help address this information-accessibility challenge.

---

##  Our Solution

SightSense provides a workflow for submitting an image and receiving a structured scene-analysis response.

The application is designed around the following process:

1. The user captures or selects an image.
2. The frontend uploads the image to the backend.
3. The backend processes the request through its configured scene-analysis components.
4. The system prepares a structured response containing scene information and risk-related information where supported.
5. The frontend displays the response in an accessible format.
6. The narration can be read aloud using browser speech synthesis.
7. If audio is available from the backend, the frontend can display an audio player.

The goal is to make the information easier to access through both visual and audio interaction.

---

##  Key Features

### 1. Image Upload and Preview

* Select an image from the user's device.
* Preview the selected image before submitting it.
* Send the image to the backend for processing.

### 2. Scene Analysis

* Submit an image to the scene-analysis API.
* Receive a structured response.
* Display observations returned by the configured analysis components.

### 3. Prioritized Scene Information

SightSense is designed to organize information around relevance to the user, rather than presenting only an unstructured list of objects.

The actual quality and reliability of prioritization depend on the configured perception and analysis components.

### 4. Risk-Related Information

* Display the risk-assessment information returned by the backend.
* Present relevant messages in the user interface.
* Support future improvements to hazard classification and prioritization.

Risk-related outputs should be treated as advisory and may be incorrect or incomplete.

### 5. Accessible Narration

* Display generated narration text.
* Use browser text-to-speech to read narration aloud.
* Support audio playback when a valid backend audio URL is returned.

### 6. Session Support

The application supports session-related functionality through the backend API, allowing analysis requests to be associated with a session where supported.

### 7. API Documentation

The backend exposes interactive API documentation through Swagger UI when the development server is running.

---

##  How It Works

```text
┌──────────────────────────────┐
│         User Interface       │
│                              │
│  Select image / Preview      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        Frontend Upload       │
│                              │
│  Send image to backend API   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│          FastAPI API         │
│                              │
│  Validate and process input  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Scene Analysis Layer    │
│                              │
│  Configured perception and   │
│  analysis components         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Response Generation     │
│                              │
│  Observations, risk-related  │
│  information, narration      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Audio and Output       │
│                              │
│  Display response, speak     │
│  narration, play audio       │
│  when available              │
└──────────────────────────────┘
```

---

##  System Architecture

SightSense follows a frontend-backend architecture.

### Frontend

The frontend provides the user-facing experience:

* Image selection and preview.
* API communication.
* Session-related interactions.
* Display of scene-analysis results.
* Narration presentation.
* Browser-based speech synthesis.
* Audio playback when an audio URL is available.

### Backend

The backend is responsible for:

* Exposing REST API endpoints.
* Receiving and validating image uploads.
* Managing analysis requests.
* Calling configured perception and analysis components.
* Preparing structured responses.
* Integrating text-to-speech functionality where configured.
* Returning request and response metadata.

### Perception and Analysis

The perception layer processes the submitted image using the implementation configured for the current environment.

Depending on the configuration, this may use development adapters or a model-backed perception implementation.

The availability of model weights, dependencies, and configuration determines which implementation can run.

### Audio

SightSense supports narration through:

* Browser speech synthesis on the frontend.
* AWS Polly integration in the backend, where configured and available.

---

## Technology Stack

| Component            | Technology           |
| -------------------- | -------------------- |
| Frontend framework   | Next.js 14           |
| Frontend language    | TypeScript           |
| UI styling           | Tailwind CSS         |
| Backend framework    | FastAPI              |
| Backend language     | Python               |
| API server           | Uvicorn              |
| Data validation      | Pydantic             |
| Cloud text-to-speech | Amazon Polly         |
| AWS SDK              | Boto3                |
| API documentation    | Swagger UI / OpenAPI |
| Version control      | Git and GitHub       |

> The exact set of enabled models and cloud services depends on the project configuration.

---

##  Project Structure

The project is organized into a frontend application, backend API, and supporting services.

```text
SightSense/
│
├── apps/
│   └── api/
│       ├── src/
│       │   └── sightsense_api/
│       │       └── main.py
│       └── ...
│
├── services/
│   └── ...
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── ...
```

> This is a simplified overview. Update it to match the actual folders and files in your repository.

---

## Getting Started

Follow these instructions to run the development version locally.

### Prerequisites

Install the following:

* Python compatible with the project's dependencies.
* Node.js and npm compatible with the frontend.
* Git.
* An AWS account and configured credentials if you want to use AWS Polly.
* Any model files and dependencies required by the selected perception implementation.

Check your installed versions:

```powershell
python --version
node --version
npm --version
git --version
```

---

##  Clone the Repository

Replace `YOUR_USERNAME` with the GitHub username or organization that owns the repository.

```powershell
git clone https://github.com/YOUR_USERNAME/SightSense.git
cd SightSense
```

If the repository is already on your computer, open PowerShell in the existing project directory instead.

---

##  Backend Setup

### 1. Navigate to the API directory

```powershell
cd D:\SightSense\apps\api
```

If you cloned the repository into another directory, use that location instead.

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can temporarily allow scripts for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

Install dependencies using the method configured by the repository.

For a project configured with `pyproject.toml`, from the repository root you may use:

```powershell
python -m pip install -e .
```

If the project instead provides a requirements file, use the appropriate command:

```powershell
python -m pip install -r requirements.txt
```

> Use the installation method that matches the actual dependency configuration in the repository. Do not run both commands unless the project requires it.

---

##  Environment Configuration

Create a local `.env` file using the provided example:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the values required by your local environment.

Example placeholders:

```dotenv
# Application
APP_ENV=development

# AWS
AWS_REGION=us-east-1

# Local development configuration
USE_LOCAL_ADAPTERS=True
ASSIST_FRAME_THROTTLE_SECONDS=2
```

> The values above are illustrative. Keep only variables that are actually supported by your application's settings. Refer to `.env.example` and the backend configuration for the authoritative list.

### Important Security Notes

* Never commit `.env`.
* Never publish AWS access keys, secret keys, session tokens, or passwords.
* Keep `.env.example` limited to variable names and safe placeholder values.
* Use IAM roles or appropriately scoped AWS credentials.
* Do not put AWS credentials in frontend environment variables.

---

##  Running the Backend

Open PowerShell and run:

```powershell
cd D:\SightSense\apps\api

$env:PYTHONPATH = "D:\SightSense;D:\SightSense\apps\api\src"

.\.venv\Scripts\Activate.ps1

python -m uvicorn sightsense_api.main:app --reload --app-dir src
```

When the server starts successfully, open:

* **API base URL:** http://127.0.0.1:8000
* **Swagger UI:** http://127.0.0.1:8000/docs
* **OpenAPI schema:** http://127.0.0.1:8000/openapi.json

Keep the backend terminal running while using the frontend.

---

## Running the Frontend

Open a separate PowerShell terminal.

Navigate to the frontend directory:

```powershell
cd D:\SightSense
```

Install frontend dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Open the local URL shown in the terminal, commonly:

```text
http://localhost:3000
```

If the frontend is configured to use a different backend URL, update the relevant frontend environment variable or configuration according to the project.

---

##  API Overview

SightSense exposes API endpoints for frontend communication and scene analysis.

The precise routes and request schemas are defined by the running backend's OpenAPI documentation.

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

### Image Analysis

The frontend submits an image to the backend using a multipart form upload.

The image field used by the current frontend is:

```text
image
```

The frontend may also send an authorization header during development:

```http
Authorization: Bearer dev-user
```

> This development token is not production authentication. Replace it with a secure authentication system before deploying to real users.

### Response Structure

The backend uses a response envelope similar to:

```json
{
  "data": {
    "risk_assessment": {},
    "narration": {
      "text": "Example narration"
    },
    "audio": {
      "audio_url": null
    }
  },
  "request_id": "example-request-id",
  "timestamp": "example-timestamp"
}
```

This is an illustrative response shape. Refer to the live API documentation for the exact schema and required fields.

### Audio Retrieval

Where audio is successfully generated and stored, the API may return an audio URL that the frontend can use for playback.

Audio generation or playback may be unavailable if cloud configuration, synthesis, storage, or network access fails.

---

##  AWS Integration

SightSense includes integration with Amazon Polly for text-to-speech functionality.

### Amazon Polly

Amazon Polly converts text into spoken audio.

In SightSense, Polly can be used to synthesize narration generated by the backend.

### Boto3

Boto3 is the AWS SDK for Python and is used by the backend to communicate with AWS services.

### Configuration

AWS Polly usage requires:

* An AWS account.
* AWS credentials configured securely.
* An appropriate AWS region.
* IAM permissions for the required Polly operations.
* A supported voice and synthesis configuration.

### Cost Awareness

AWS services may incur charges depending on usage, region, service configuration, and available credits.

Monitor AWS billing and usage. Do not assume that all AWS usage is free.

---

##  Testing

Testing should cover both backend behavior and frontend interactions.

### Backend Checks

* Confirm that the API starts successfully.
* Open Swagger UI.
* Submit a valid image.
* Verify that the API returns a structured response.
* Test invalid or missing image input.
* Check behavior when audio generation is unavailable.
* Verify that errors are handled without exposing secrets.

### Frontend Checks

* Confirm that the application loads.
* Select an image and verify its preview.
* Submit the image.
* Verify that the response is displayed.
* Test the narration control.
* Test audio playback when a valid audio URL is returned.
* Check behavior when the backend is unavailable.

### Manual Testing

Use Swagger UI to inspect and test the API endpoints:

```text
http://127.0.0.1:8000/docs
```

> Add automated test commands here once the project's test suite and commands are confirmed.

---

##  Security and Privacy

SightSense is intended to support accessibility, so user privacy and safety are important design considerations.

Recommended safeguards include:

* Do not commit credentials or secrets.
* Avoid storing uploaded images longer than necessary.
* Restrict access to user-specific analysis results.
* Validate image uploads and enforce size limits.
* Use HTTPS for deployed environments.
* Replace development authentication with secure authentication.
* Avoid logging sensitive image content or personal information.
* Provide clear information about how images and generated audio are processed.
* Apply appropriate access controls to cloud resources.

These safeguards should be verified and implemented before production deployment.

---

## Limitations

SightSense is a developing assistive technology project. Its outputs may be incomplete or inaccurate.

Potential limitations include:

* Scene-analysis accuracy depends on the configured perception implementation.
* Development adapters may return simulated or predefined outputs rather than actual model predictions.
* Performance may vary with image quality, lighting, occlusion, and environmental complexity.
* Risk assessments may fail to identify hazards or may report risks that are not present.
* Text-to-speech availability depends on browser support or backend audio generation.
* Network connectivity may affect response time and cloud functionality.
* The current interface may not yet be optimized for every accessibility need or assistive device.

**SightSense must not be used as the sole basis for navigation or safety-critical decisions.** Users should continue to rely on established mobility aids and their own situational awareness.

---

##  Future Enhancements

Potential future improvements include:

* Real-time camera assistance.
* Improved object detection and scene understanding.
* More reliable hazard identification and prioritization.
* Support for additional Indian languages.
* Context-aware narration.
* Improved low-latency audio feedback.
* Mobile-first experience.
* Offline inference where feasible.
* More extensive accessibility testing with visually impaired users.
* Stronger authentication and session management.
* Privacy-preserving image processing.
* Automated testing and deployment pipelines.
* Performance, reliability, and safety evaluation.

---

##  Team

### Team Lead

**Nandini Kuncham**

Responsibilities:

* Defined project objectives and helped plan the system architecture.
* Coordinated frontend and backend development.
* Guided integration of application components.
* Tested AWS Polly integration using Boto3.
* Coordinated tasks and troubleshooting.
* Supported workflow testing and demo preparation.


##  Acknowledgements

We acknowledge the open-source technologies and cloud services that support the development of SightSense, including:

* Next.js
* FastAPI
* Python
* TypeScript
* Tailwind CSS
* Amazon Polly
* Boto3
* The broader accessibility and assistive-technology community

---

<p align="center">
  <strong>SightSense — Making environmental information more accessible.</strong>
</p>
