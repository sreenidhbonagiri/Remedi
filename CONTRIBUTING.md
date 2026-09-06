# Contributing to Remedi 💊

Thank you for your interest in contributing to Remedi! We are building an open-source clinical advocacy engine to help patients identify bioequivalent generic alternatives and navigate patient assistance programs.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful and constructive in all interactions.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Git

### Local Setup

1. Fork the repository on GitHub, then clone your fork:
   git clone https://github.com/YOUR_USERNAME/Remedi.git
   cd Remedi

2. Create a virtual environment:
   python -m venv venv
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Verify the test suite:
   pytest

5. Run the local development server:
   uvicorn app.main:app --reload

---

## Finding Something to Work On

Check our open issues on GitHub:
- good first issue: Beginner-friendly tasks scoped to a specific file.
- enhancement: Proposed feature additions or performance optimizations.
- bug: Reported errors or edge cases.

---

## Guidelines

1. Create a feature branch: git checkout -b feat/your-feature-name
2. Follow PEP 8 style standards.
3. Ensure all tests pass with pytest before opening a pull request.
