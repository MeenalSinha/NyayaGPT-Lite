# Changelog

All notable changes to NyayaGPT Lite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-22

### Added
- Initial release of NyayaGPT Lite
- React-based frontend with bilingual support (English & Hindi)
- FastAPI backend for document processing
- Document type detection (FIR, Court Order, Legal Notice)
- AI-powered explanation with structured output
- Transparent AI reasoning ("Why This Explanation?" section)
- Confidence & Limits card showing AI capabilities
- Real-world impact story on landing page
- Quick impact metrics box (saves 2-3 lawyer visits, <30 seconds)
- Demo mode with clear production model explanation
- PDF upload and text paste functionality
- Section highlighting with legal explanations
- Legal pathway guidance (non-advisory)
- Voice explanation feature
- Suggested follow-up questions
- Help & resources section (Legal Aid, Lok Adalat)
- Responsive design for mobile and desktop
- Complete documentation suite
- Kaggle training notebook for model fine-tuning
- Docker deployment configuration
- CI/CD pipeline with GitHub Actions

### Features by Category

#### Core Functionality
- Document upload (PDF & text)
- Bilingual explanation (English/Hindi)
- Structured output format
- Document type auto-detection

#### Responsible AI
- Permanent disclaimer banner
- "What AI Can/Cannot Do" card
- Transparent reasoning display
- No outcome predictions
- Encourages lawyer consultation

#### User Experience
- 30-second explanation promise
- Plain language mode
- Visual progress indicators
- Suggested questions
- Help resources

#### Technical
- Fine-tuned Mistral-7B architecture
- LoRA/QLoRA implementation
- FastAPI REST API
- React + Tailwind UI
- Docker containerization

### Documentation
- Comprehensive README
- Pitch presentation guide
- Deployment instructions
- Dataset preparation guide
- Contributing guidelines
- 30-second judge narrative
- 99-point improvement summary

### Known Limitations
- Demo mode uses structured outputs (production uses fine-tuned model)
- Currently supports 2 languages (English & Hindi)
- Limited to text-based documents
- Requires internet connection

## [Unreleased]

### Planned for v1.1.0
- Integration with fine-tuned model
- Additional Indian languages (Tamil, Telugu, Bengali)
- Voice input support
- Mobile app (React Native)
- Offline mode
- User feedback collection
- Analytics dashboard

### Planned for v1.2.0
- More document types (Bail Orders, Summons, Judgments)
- Case status tracking
- Legal aid organization integration
- Multi-document comparison
- Timeline visualization
- Bookmark and save features

### Planned for v2.0.0
- All 22 Indian languages
- Integration with eCourts API
- Voice conversation mode
- Community features
- Legal professional verification
- Advanced analytics
- Mobile apps (iOS & Android)

---

## Version History

- v1.0.0 (2025-01-22) - Initial hackathon release
- v0.9.0 (2025-01-20) - Beta testing
- v0.5.0 (2025-01-15) - Alpha prototype

---

**Legend:**
- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements
