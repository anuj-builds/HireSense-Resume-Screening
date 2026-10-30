# AI-Based Resume Screening and Candidate Shortlisting System

An AI-assisted resume screening platform that helps recruiters upload resumes, extract candidate information, compare skills with job requirements, rank candidates, and manage shortlisted applicants.

## Features

- Upload and manage resumes
- Extract text from supported resume documents
- Match candidate skills against job requirements
- Rank candidates based on matching results
- Shortlist candidates
- React-based dashboard
- FastAPI REST API
- Automated backend tests

## Tech Stack

**Frontend:** React, Vite, JavaScript

**Backend:** Python, FastAPI, SQLAlchemy, Pydantic

**Testing:** Pytest

## Project Structure

```text
ResumeScreening/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

## Prerequisites

Install the following on your computer:

- Python 3.10 or a compatible version supported by the project dependencies
- Node.js and npm
- Git

## Backend Setup

Open a terminal in the project root and run:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows Command Prompt:

```bat
.venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

Interactive API documentation: `http://127.0.0.1:8000/docs`

## Frontend Setup

Open a second terminal in the project root:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

Keep both the backend and frontend running while using the application.

## Running Backend Tests

Open a terminal in the backend directory, activate the virtual environment, and run:

```bash
python -m pytest -v
```

## API Overview

The backend currently includes endpoints for:

- Health checks: `/api/v1/health/`
- Resume upload and retrieval: `/api/v1/resumes/`
- Candidate ranking: `/api/v1/screening/{job_id}/rank`
- Candidate shortlisting: `/api/v1/screening/{job_id}/shortlist/{resume_id}`

For request formats and available operations, open the Swagger documentation at `/docs`.

## Notes

- Install dependencies separately on every new computer.
- Local virtual environments and frontend `node_modules` are not committed to Git.
- Local databases and uploaded resumes may need to be recreated when setting up on a new computer.
- Do not commit real candidate resumes, credentials, API keys, or `.env` files.
- Confirm the required Python version and database configuration against the current backend settings before deployment.

## Future Improvements

- Multiple job creation and selection
- Enhanced candidate comparison and skill-gap analysis
- Exportable shortlist reports
- Improved validation and error handling
- Additional automated tests
- UI and accessibility improvements
