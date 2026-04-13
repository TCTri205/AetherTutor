# Hướng Dẫn Đóng Góp (Contributing Guide)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 12, 2026
> **Version:** 2.0
> **Status:** Active

---

Chào mừng bạn đến với cộng đồng phát triển AetherTutor! Tài liệu này cung cấp các quy chuẩn và quy trình để đóng góp mã nguồn cho dự án.

---

## 1. Code of Conduct

### Our Pledge

We pledge to make participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior:**
- The use of sexualized language or imagery and unwelcome sexual attention
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

---

## 2. How Can I Contribute?

### 2.1 Reporting Bugs

**Before submitting a bug report:**
- Check the [existing issues](https://github.com/aethertutor/aethertutor/issues)
- Search the [documentation](docs/)
- Try to reproduce on the latest version

**Bug report template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment:**
 - OS: [e.g. Windows 11, macOS 14, Ubuntu 22.04]
 - Python: [e.g. 3.11.5]
 - AetherTutor Version: [e.g. v0.3.0]
 - LLM Provider: [OpenAI / Ollama]

**Additional context**
Add any other context about the problem here.

**Logs**
```
[Paste relevant error logs here]
```
```

### 2.2 Suggesting Features

**Before submitting a feature request:**
- Check [existing feature requests](https://github.com/aethertutor/aethertutor/issues?q=is%3Aissue+label%3Aenhancement)
- Review the [Roadmap](reports/2026-04-07_product_roadmap.md) to see if it's already planned

**Feature request template:**

```markdown
**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Learning Theory Alignment**
Which learning theory does this feature support? (e.g., Active Recall, Spaced Repetition, Constructivism)

**Priority**
How important is this feature to your workflow?
- [ ] Critical (blocking)
- [ ] High (major improvement)
- [ ] Medium (nice to have)
- [ ] Low (minor enhancement)
```

### 2.3 Pull Requests

**Before submitting a PR:**
- Fork the repository and create your branch from `main`
- Ensure your code follows the [style guide](#3-coding-standards)
- Write tests for new functionality
- Update documentation if needed
- All tests must pass

**PR template:**

```markdown
## Description
Brief description of changes (what and why)

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Related Issues
Fixes #123, Closes #456

## Testing
Describe how you tested these changes:
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

**Test instructions:**
```bash
# How to run tests
pytest tests/unit/test_new_feature.py -v
```

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Learning Impact (if applicable)
Which learning theory does this change support?
- [ ] Active Recall
- [ ] Spaced Repetition (SM-2)
- [ ] Feynman Technique
- [ ] Dual Coding
- [ ] Zettelkasten
- [ ] First Principles
- [ ] Other: __________
```

---

## 3. Coding Standards

### 3.1 General Principles

- **Clean Code:** Functions should do one thing well
- **DRY:** Don't Repeat Yourself - extract common logic
- **SOLID:** Follow SOLID principles for OOP
- **KISS:** Keep It Simple, Stupid
- **YAGNI:** You Aren't Gonna Need It

### 3.2 Python Style Guide

We use **Ruff** for linting and formatting (replaces Black + isort):

```python
# Line length: 100 characters (Ruff default)
# Type hints: Required for all function signatures
# Docstrings: Google style

from typing import Optional
from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    """Request model for user registration."""

    email: str
    password: str
    name: str
    accept_terms: bool


async def create_user(
    email: str,
    password: str,
    name: str,
    db_session: AsyncSession
) -> User:
    """
    Create a new user account.

    Args:
        email: User's email address (must be unique)
        password: User's password (will be hashed)
        name: User's display name
        db_session: Database session

    Returns:
        Created User object

    Raises:
        DuplicateEmailError: If email already exists
        ValidationError: If input validation fails
    """
    # Check for existing user
    existing = await db_session.execute(
        select(User).where(User.email == email)
    )

    if existing.scalar_one_or_none():
        raise DuplicateEmailError(email)

    # Hash password and create user
    hashed_password = hash_password(password)
    user = User(
        email=email,
        password_hash=hashed_password,
        name=name
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user
```

**Linting & Formatting:**
```bash
# Install ruff
pip install ruff

# Format code
ruff format app/ tests/

# Lint code
ruff check app/ tests/

# Fix auto-fixable issues
ruff check app/ tests/ --fix
```

### 3.3 TypeScript/React Style Guide

```typescript
// Components: PascalCase
// Hooks: camelCase with 'use' prefix
// Types/Interfaces: PascalCase
// Constants: UPPER_SNAKE_CASE

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';

interface FlashcardProps {
  /** Front content of the flashcard */
  front: React.ReactNode;
  /** Back content of the flashcard */
  back: React.ReactNode;
  /** Called when user rates difficulty */
  onRate: (quality: number) => void;
  /** Initial flipped state */
  initialFlipped?: boolean;
}

/**
 * Interactive flashcard component with flip animation
 * 
 * @example
 * ```tsx
 * <Flashcard
 *   front="What is quantum superposition?"
 *   back="A quantum system can exist in multiple states..."
 *   onRate={(quality) => handleReview(quality)}
 * />
 * ```
 */
export function Flashcard({
  front,
  back,
  onRate,
  initialFlipped = false,
}: FlashcardProps): JSX.Element {
  const [isFlipped, setIsFlipped] = useState(initialFlipped);
  
  const handleFlip = useCallback(() => {
    setIsFlipped(prev => !prev);
  }, []);
  
  return (
    <div
      className={`flashcard ${isFlipped ? 'flipped' : ''}`}
      onClick={handleFlip}
      role="button"
      tabIndex={0}
      aria-pressed={isFlipped}
    >
      <div className="flashcard-inner">
        <div className="flashcard-front">
          {front}
        </div>
        <div className="flashcard-back">
          {back}
        </div>
      </div>
    </div>
  );
}
```

**Frontend linting:**
```bash
# Install dependencies
npm install

# Lint
npm run lint

# Type check
npm run type-check

# Format
npm run format

# Test
npm run test

# All checks
npm run validate
```

### 3.4 Git Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no behavior change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependencies

**Examples:**
```bash
feat(auth): add OAuth2 login support
fix(sm2): correct interval calculation for failed recalls
docs(api): update flashcard endpoint documentation
refactor(rag): extract chunking logic to separate module
perf(db): add index on flashcards next_review column
test(agents): add unit tests for Socratic tutor
chore(deps): update langchain to v0.1.0
```

**Scope values:** `auth`, `sm2`, `api`, `rag`, `graph`, `db`, `worker`, `chat`, `quiz`, `flashcard`, `note`, `docs`, `worker`, `deps`, `ui`

---

## 4. Development Workflow

### 4.1 Branch Strategy

```
main (production)
  ↑
feature/* (new features)
bugfix/* (bug fixes)
hotfix/* (urgent fixes)
```

**Branch naming:**
```
feature/RAG-pipeline          # New feature
bugfix/SM2-calculation        # Bug fix
hotfix/auth-bypass            # Urgent security fix
```

### 4.2 Development Process

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/aethertutor.git
cd AetherTutor

# 2. Add upstream remote
git remote add upstream https://github.com/aethertutor/aethertutor.git

# 3. Create feature branch
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name

# 4. Make changes and commit
git add .
git commit -m "feat(scope): description"

# 5. Keep branch up to date
git fetch upstream
git rebase upstream/main

# 6. Push to your fork
git push origin feature/your-feature-name

# 7. Create Pull Request on GitHub
```

### 4.3 Local Development Setup

```bash
# Prerequisites
# - Python 3.11+
# - Node.js 20+
# - PostgreSQL 16
# - Redis 7
# - Docker & Docker Compose (optional)

# 1. Start data layer (PostgreSQL, Redis, ChromaDB)
docker compose -f docker-compose.data.yml up -d

# 2. Backend setup
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# 3. Start Worker (terminal 1)
arq app.worker.tasks.WorkerSettings

# 4. Start API (terminal 2)
uvicorn app.main:app --reload --port 8000

# 5. Frontend setup (terminal 3)
cd frontend
npm install
npm run dev
```

**Truy cập Local:**
- **Frontend (Vite):** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`

### 4.4 Docker Development (Full Stack)

```bash
# Start all services
docker compose up --build -d

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

---

## 5. Testing Requirements

### 5.1 Test Coverage

- **Minimum coverage:** 80% (target)
- **Critical modules:** 100% (SM-2, auth, data isolation)
- **No decrease** in coverage after merge

**Current status:**
- **39 test files** trong `tests/`
- **225+ test functions**
- **2 lớp tests:** Unit + Integration
- **CI:** GitHub Actions runs pytest + coverage on every PR

### 5.2 Test Structure

```
tests/
├── conftest.py              # Shared fixtures: test_db, async_client, mock_llm
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_*.py
│   └── ...
├── integration/             # Integration tests (API + DB + Worker)
│   ├── test_*.py
│   └── ...
└── mocks/                   # Mock fixtures
    ├── mock_llm.py
    └── ...
```

### 5.3 Writing Tests

```python
# tests/unit/test_example.py
import pytest
from app.services.example import ExampleService


class TestExampleService:
    """Tests for ExampleService."""

    async def test_method_success(self):
        """Should return expected result."""
        service = ExampleService()
        result = await service.method("input")
        assert result.expected_field == "value"

    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    async def test_method_various_inputs(self, input, expected):
        """Should handle different input values."""
        service = ExampleService()
        result = await service.method(input)
        assert result == expected
```

### 5.4 Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_sm2.py -v

# Run tests matching keyword
pytest -k "flashcard" -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Stop on first failure
pytest -x

# Coverage report
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### 5.5 Pre-Commit Checklist

Trước khi push code:

```bash
# 1. Lint
ruff check app/ tests/

# 2. Format
ruff format app/ tests/

# 3. Run tests
pytest tests/unit/ tests/integration/ -v
```

---

## 6. Documentation Standards

### 6.1 Code Documentation

- **Modules:** Brief description at top of file
- **Functions:** Docstrings with Args, Returns, Raises
- **Classes:** Class-level docstring explaining purpose
- **Complex logic:** Inline comments explaining WHY (not WHAT)

### 6.2 Documentation Updates

Update documentation when:
- Adding new features
- Changing API endpoints
- Modifying configuration
- Updating dependencies (if breaking changes)

**Documentation checklist:**
- [ ] README.md updated
- [ ] API documentation updated
- [ ] Changelog entry added
- [ ] Migration guide (if breaking change)
- [ ] Code examples updated

### 6.3 Translation Guidelines

We support multiple languages:
- `docs/` - English (primary)
- `docs/vi/` - Vietnamese

When adding new documentation:
1. Create in English first
2. Add to translation tracking issue
3. Translate to Vietnamese (if possible)
4. Update language selector in docs

---

## 7. Review Process

### 7.1 Code Review Checklist

**Before approving, reviewers should verify:**
- [ ] Code follows style guide
- [ ] Tests are comprehensive
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered
- [ ] Error handling appropriate
- [ ] Logging added for debugging
- [ ] No hardcoded secrets or credentials

### 7.2 Review Timeline

| PR Size | Review Time | Examples |
|---|---|---|
| Small (1-50 lines) | 4 hours | Bug fix, typo, docs |
| Medium (50-200 lines) | 24 hours | Feature enhancement |
| Large (200-500 lines) | 48 hours | New feature |
| XL (500+ lines) | 72 hours | Major refactor |

### 7.3 Approval Requirements

- **Small PRs:** 1 approval
- **Medium PRs:** 2 approvals
- **Large PRs:** 2 approvals + tech lead
- **Breaking changes:** 2 approvals + tech lead + PM

---

## 8. Release Process

### 8.1 Versioning

We follow [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
  ↑     ↑     ↑
  |     |     └─ Backward-compatible bug fixes
  |     └─────── Backward-compatible new features
  └───────────── Incompatible API changes
```

**Examples:**
- `1.0.0` - Initial release
- `1.1.0` - New features
- `1.1.1` - Bug fixes
- `2.0.0` - Breaking changes

### 8.2 Release Checklist

```bash
# 1. Create release branch
git checkout -b release/v1.1.0 develop

# 2. Update version numbers
# - pyproject.toml
# - package.json
# - docs/Changelog.md

# 3. Run full test suite
make test-all

# 4. Build and test locally
docker build -t aethertutor:1.1.0 .
docker-compose -f docker-compose.prod.yml up

# 5. Create PR to main
gh pr create --base main --title "Release v1.1.0"

# 6. After merge, tag release
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0

# 7. Create GitHub Release
gh release create v1.1.0 --generate-notes

# 8. Deploy to production
make deploy-prod
```

---

## 9. Getting Help

### 9.1 Communication Channels

| Channel | Purpose | Link |
|---|---|---|
| **GitHub Discussions** | Feature requests, questions | https://github.com/aethertutor/aethertutor/discussions |
| **Discord** | Real-time chat | https://discord.gg/aethertutor |
| **Email** | Private inquiries | team@aethertutor.com |
| **Twitter** | Updates & announcements | [@AetherTutor](https://twitter.com/aethertutor) |

### 9.2 Office Hours

- **Weekly:** Wednesday 2-4 PM UTC+7
- **Location:** Discord voice channel
- **Agenda:** Open Q&A, pair programming sessions

### 9.3 Resources

- [Documentation](https://docs.aethertutor.com)
- [API Reference](https://api.aethertutor.com/docs)
- [Architecture Overview](core/Architecture.md)
- [Testing Guide](future_ops/Testing_Strategy.md)
- [Security Policy](future_ops/Security_Privacy.md)

---

## 10. Recognition

Contributors are recognized in multiple ways:

- **README.md:** All contributors listed
- **Releases:** Notable contributions highlighted
- **Website:** Contributor wall of fame
- **Swag:** Top contributors receive stickers, t-shirts

**Current Contributors:**

```markdown
<!-- Add yourself to this list when your PR is merged -->
- John Doe (@johndoe) - Initial architecture
- Jane Smith (@janesmith) - SM-2 implementation
- Your Name (@yourname) - Your contribution
```

---

> [!TIP]
> First time contributor? Look for issues labeled `good-first-issue` or `help-wanted`.
> Don't hesitate to ask questions - we're here to help!

---
© 2026 AetherTutor Team. Last updated: April 5, 2026
