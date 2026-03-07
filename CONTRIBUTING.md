# Contributing to NyayaGPT Lite

Thank you for your interest in contributing to NyayaGPT Lite! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Prioritize the project's mission: making legal information accessible

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Use the bug report template
3. Include:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Environment details (OS, browser, etc.)

### Suggesting Enhancements

1. Check if the enhancement has been suggested
2. Use the feature request template
3. Explain:
   - The problem it solves
   - How it aligns with project goals
   - Potential implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m "Add: feature description"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request

#### PR Guidelines

- One feature/fix per PR
- Update documentation if needed
- Add tests if applicable
- Ensure CI passes
- Request review from maintainers

### Commit Message Format

```
Type: Brief description

Detailed explanation (if needed)

Types: Add, Update, Fix, Remove, Refactor, Docs, Test
```

Examples:
- `Add: Hindi translation for help section`
- `Fix: PDF upload validation error`
- `Update: Improve explanation clarity for FIRs`

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full Stack (Docker)

```bash
docker-compose up --build
```

## Code Style

### Python (Backend)
- Follow PEP 8
- Use type hints
- Add docstrings for functions
- Maximum line length: 88 characters (Black formatter)

### JavaScript/React (Frontend)
- Use functional components
- Follow React hooks best practices
- Use meaningful variable names
- Add comments for complex logic

### Formatting
- Backend: Use `black` and `flake8`
- Frontend: Use `prettier` and `eslint`

## Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for >80% code coverage

### Running Tests

Backend:
```bash
cd backend
pytest
```

Frontend:
```bash
cd frontend
npm test
```

## Documentation

- Update README.md if needed
- Add inline comments for complex code
- Update API documentation for new endpoints
- Keep CHANGELOG.md updated

## Priority Areas

High-impact contributions:

1. **Additional Languages**
   - Tamil, Telugu, Bengali, Marathi translations
   - Regional legal terminology

2. **Document Types**
   - More legal document templates
   - Better parsing for complex documents

3. **Accessibility**
   - Screen reader compatibility
   - Keyboard navigation
   - Voice input/output

4. **Training Data**
   - Anonymized legal documents
   - Quality dataset curation

5. **Model Improvements**
   - Fine-tuning optimizations
   - Better prompt engineering

## Legal & Ethical Guidelines

### MUST Follow:

1. **No Legal Advice**: Never add features that provide legal advice
2. **Privacy**: No collection of sensitive personal data
3. **Disclaimers**: Maintain all legal disclaimers
4. **Accuracy**: Verify legal information with professionals
5. **Anonymization**: Always anonymize training data

### Prohibited:

- Predicting case outcomes
- Providing legal strategy advice
- Collecting user personal information
- Removing safety guardrails

## Getting Help

- Open a Discussion for questions
- Tag maintainers in Issues
- Join community chat (if available)

## Recognition

Contributors will be:
- Listed in README.md
- Acknowledged in release notes
- Credited in documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make legal information accessible to all Indians! 🙏
