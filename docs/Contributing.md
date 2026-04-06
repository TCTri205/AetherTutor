# Hướng Dẫn Đóng Góp (Contributing Guide)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 5, 2026
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
- Search the [documentation](https://docs.aethertutor.com)
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

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. Windows 10, macOS 13.0, Ubuntu 22.04]
 - Browser: [e.g. Chrome 120, Safari 17]
 - AetherTutor Version: [e.g. 1.0.0]
 - Python Version: [e.g. 3.10.5]

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
- Review the [Roadmap](Roadmap.md) to see if it's already planned

**Feature request template:**

```markdown
**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context, screenshots, or mockups about the feature request here.

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
- Fork the repository and create your branch from `develop`
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
- [ ] E2E tests added/updated

**Test instructions:**
```bash
# How to run tests
pytest tests/test_new_feature.py
```

## Screenshots (if applicable)
Add screenshots or GIFs showing the feature in action

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

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

We follow [PEP 8](https://peps.python.org/pep-0008/) with these modifications:

```python
# Line length: 100 characters (not 79)
# String quotes: Double quotes for consistency
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
# Install dev dependencies
pip install -r requirements-dev.txt

# Format code (Black)
black aethertutor/ tests/

# Sort imports (isort)
isort aethertutor/ tests/

# Type checking (mypy)
mypy aethertutor/

# Linting (ruff)
ruff check aethertutor/

# All checks (CI hook)
make lint
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

**Git Hook (pre-commit):**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  
  - repo: https://github.com/astral-sh/ruff
    rev: v0.1.11
    hooks:
      - id: ruff
  
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest tests/unit -x
        language: system
        pass_filenames: false
        always_run: true
```

---

## 4. Development Workflow

### 4.1 Branch Strategy

```
main (production)
  ↑
develop (staging)
  ↑
feature/* (new features)
bugfix/* (bug fixes)
hotfix/* (urgent fixes)
release/* (release prep)
```

**Branch naming:**
```
feature/RAG-pipeline          # New feature
bugfix/SM2-calculation        # Bug fix
hotfix/auth-bypass            # Urgent security fix
release/v1.0.0               # Release preparation
```

### 4.2 Development Process

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/aethertutor.git
cd aethertutor

# 2. Add upstream remote
git remote add upstream https://github.com/aethertutor/aethertutor.git

# 3. Create feature branch
git checkout develop
git pull upstream develop
git checkout -b feature/your-feature-name

# 4. Make changes and commit
git add .
git commit -m "feat(scope): description"

# 5. Keep branch up to date
git fetch upstream
git rebase upstream/develop

# 6. Push to your fork
git push origin feature/your-feature-name

# 7. Create Pull Request on GitHub
```

### 4.3 Local Development Setup

```bash
# Prerequisites
# - Python 3.10+
# - Node.js 18+
# - PostgreSQL 15+
# - Redis 7+

# Backend setup
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt

cp .env.example .env
# Edit .env with your configuration

# Database setup
createdb aethertutor_dev
alembic upgrade head

# Run backend
uvicorn aethertutor.app:create_app --reload --port 8000

# Frontend setup
cd frontend
npm install
cp .env.example .env
npm run dev

# Run tests
pytest tests/
npm run test  # frontend
```

### 4.4 Docker Development

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f api

# Run tests in container
docker-compose -f docker-compose.dev.yml run api pytest tests/

# Stop services
docker-compose -f docker-compose.dev.yml down
```

---

## 5. Testing Requirements

### 5.1 Test Coverage

- **Minimum coverage:** 80%
- **Critical modules:** 100% (SM-2, auth, payment)
- **No decrease** in coverage after merge

### 5.2 Writing Tests

```python
# tests/unit/test_example.py
import pytest
from aethertutor.example import add_numbers


class TestAddNumbers:
    """Tests for add_numbers function."""
    
    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 1, 0),
        (100, 200, 300),
    ])
    def test_add_numbers(self, a, b, expected):
        """Should return sum of two numbers."""
        assert add_numbers(a, b) == expected
    
    def test_add_numbers_with_floats(self):
        """Should handle float inputs."""
        result = add_numbers(1.5, 2.5)
        assert result == pytest.approx(4.0)
    
    def test_add_numbers_with_invalid_type(self):
        """Should raise TypeError for invalid inputs."""
        with pytest.raises(TypeError):
            add_numbers("1", 2)
```

### 5.3 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aethertutor --cov-report=html

# Run specific test file
pytest tests/unit/test_sm2.py

# Run tests matching keyword
pytest -k "flashcard"

# Run tests in parallel
pytest -n auto

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
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
- [Architecture Overview](Architecture.md)
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
