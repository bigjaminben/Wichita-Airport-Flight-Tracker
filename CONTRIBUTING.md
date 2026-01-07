# Contributing to ICT Airport Operations Intelligence Platform

Thank you for your interest in contributing to the ICT Airport Operations Intelligence Platform! This document provides guidelines for contributing to this project.

## 🏢 Project Overview

This is a **proprietary Deloitte Consulting project**. All contributions must comply with Deloitte's internal policies and procedures.

## 📋 Before Contributing

1. Ensure you have proper authorization from the project team
2. Review existing issues and pull requests to avoid duplication
3. Familiarize yourself with the codebase and architecture
4. Read the full [DOCUMENTATION.md](DOCUMENTATION.md)

## 🔄 Development Workflow

### 1. Set Up Development Environment

```powershell
# Clone the repository (internal Deloitte GitLab/GitHub)
git clone <repository-url>
cd "Flight Trackers/New folder"

# Install dependencies
py -3 -m pip install -r requirements.txt

# Optional: Set up pre-commit hooks
pre-commit install
```

### 2. Create Feature Branch

```bash
# Always branch from main/master
git checkout main
git pull origin main

# Create descriptive feature branch
git checkout -b feature/your-feature-name
# OR for bug fixes
git checkout -b bugfix/issue-description
# OR for documentation
git checkout -b docs/what-you-are-documenting
```

### 3. Make Changes

- Write clean, readable code following PEP 8
- Add docstrings to all functions and classes
- Include type hints where appropriate
- Write meaningful commit messages
- Keep commits atomic and focused

### 4. Test Your Changes

```powershell
# Run smoke tests
py -3 smoke_test.py

# Test specific functionality
py -3 -m pytest tests/

# Check code style
py -3 -m flake8 .
py -3 -m black --check .
py -3 -m mypy .
```

### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add ML model performance tracking

- Implemented accuracy metrics logging
- Added confusion matrix visualization
- Updated API endpoint for model stats
- Added tests for new functionality

Refs: JIRA-123"
```

**Commit Message Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style/formatting (no logic changes)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 6. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create pull request via GitLab/GitHub UI
```

## 📝 Code Style Guidelines

### Python Code Standards

```python
"""Module docstring explaining the module's purpose.

This module handles flight data processing and analytics
for the ICT Airport Operations Intelligence Platform.
"""

from typing import List, Dict, Optional
import pandas as pd


def process_flight_data(
    flights: List[Dict],
    include_historical: bool = False
) -> pd.DataFrame:
    """
    Process raw flight data into structured DataFrame.
    
    Args:
        flights: List of flight dictionaries from API
        include_historical: Whether to merge with historical data
        
    Returns:
        Processed flight data as DataFrame
        
    Raises:
        ValueError: If flights list is empty
        
    Example:
        >>> flights = fetch_flights_from_api()
        >>> df = process_flight_data(flights)
        >>> print(df.head())
    """
    if not flights:
        raise ValueError("Flights list cannot be empty")
    
    # Implementation
    df = pd.DataFrame(flights)
    
    return df
```

### JavaScript Code Standards

```javascript
/**
 * Fetch and display flight statistics
 * @async
 * @param {string} endpoint - API endpoint path
 * @returns {Promise<Object>} Flight statistics data
 * @throws {Error} If fetch fails
 */
async function fetchFlightStats(endpoint) {
  try {
    const response = await fetch(`/api/${endpoint}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch flight stats:', error);
    throw error;
  }
}
```

### HTML/CSS Standards

- Use semantic HTML5 elements
- Include ARIA labels for accessibility
- Follow BEM naming convention for CSS classes
- Ensure mobile responsiveness
- Support dark mode where applicable

## 🧪 Testing Requirements

### Required Tests

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test all REST endpoints
4. **UI Tests**: Test critical user flows

### Test Example

```python
import pytest
from api import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint returns 200."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] in ['healthy', 'degraded']


def test_flights_all(client):
    """Test flights endpoint returns valid data."""
    response = client.get('/api/flights/all')
    assert response.status_code == 200
    data = response.json
    assert 'flights' in data
    assert isinstance(data['flights'], list)
```

## 📚 Documentation Requirements

### Required Documentation

- **Code Comments**: Explain complex logic
- **Docstrings**: All public functions, classes, and modules
- **README Updates**: For new features or setup changes
- **API Documentation**: For new endpoints
- **UPDATES.md**: Add entry for significant changes

### Documentation Example

````python
def calculate_delay_risk(
    flight: Dict,
    weather: Dict,
    historical_data: pd.DataFrame
) -> Dict:
    """
    Calculate delay risk probability using ML model.
    
    This function combines real-time flight information,
    weather conditions, and historical patterns to predict
    the probability of flight delays.
    
    Args:
        flight: Flight information dictionary containing:
            - flight_number (str): Flight identifier
            - airline (str): Airline code
            - origin (str): Origin airport code
            - destination (str): Destination airport code
            - scheduled_time (str): ISO format datetime
        weather: Current weather conditions dictionary
        historical_data: DataFrame with past flight performance
        
    Returns:
        Dictionary containing:
            - risk_level (str): 'Low', 'Medium', or 'High'
            - risk_score (float): Probability 0-100
            - confidence (float): Model confidence 0-100
            - factors (List[str]): Contributing risk factors
            
    Raises:
        ValueError: If required flight fields are missing
        ModelError: If ML model prediction fails
        
    Example:
        >>> flight = {
        ...     'flight_number': 'AA123',
        ...     'airline': 'AA',
        ...     'origin': 'DFW',
        ...     'destination': 'ICT'
        ... }
        >>> weather = fetch_weather('ICT')
        >>> risk = calculate_delay_risk(flight, weather, history_df)
        >>> print(f"Risk: {risk['risk_level']} ({risk['risk_score']}%)")
        Risk: Medium (65%)
    """
    # Implementation
    pass
````

## 🔍 Code Review Process

### Review Checklist

**Functionality:**
- [ ] Code works as intended
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] Performance is acceptable

**Code Quality:**
- [ ] Follows PEP 8 / style guide
- [ ] No duplicate code
- [ ] Meaningful variable/function names
- [ ] Appropriate comments and docstrings

**Testing:**
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Test coverage is adequate (>80%)

**Documentation:**
- [ ] README updated if needed
- [ ] API docs updated
- [ ] Code comments are clear
- [ ] UPDATES.md entry added

**Security:**
- [ ] No sensitive data in code
- [ ] Input validation implemented
- [ ] No SQL injection vulnerabilities
- [ ] Dependencies are secure

### Review Process

1. **Self-Review**: Review your own PR first
2. **Automated Checks**: Ensure CI/CD pipeline passes
3. **Peer Review**: At least one team member reviews
4. **Address Feedback**: Make requested changes
5. **Approval**: Get approval from maintainer
6. **Merge**: Squash and merge to main

## 🐛 Bug Reports

### Creating a Bug Report

**Title**: Clear, concise description

**Template**:
```markdown
## Bug Description
[Clear description of the bug]

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS: Windows 10/11
- Python Version: 3.10.x
- Browser: Chrome 120.x
- Node.js: 14.x

## Screenshots
[If applicable]

## Logs
```
[Paste relevant logs]
```

## Additional Context
[Any other relevant information]
```

## ✨ Feature Requests

### Creating a Feature Request

**Title**: Concise feature description

**Template**:
```markdown
## Feature Description
[Clear description of the proposed feature]

## Use Case
[Why is this feature needed? Who will use it?]

## Proposed Solution
[How should it work?]

## Alternatives Considered
[Other solutions you've thought about]

## Additional Context
[Mockups, diagrams, examples]
```

## 🚀 Release Process

1. **Version Bump**: Update version in relevant files
2. **Changelog**: Update UPDATES.md with changes
3. **Testing**: Full regression testing
4. **Tag**: Create git tag `v2.x.x`
5. **Deploy**: Follow deployment checklist
6. **Announce**: Notify team of new release

## 📞 Getting Help

- **Documentation**: Read [DOCUMENTATION.md](DOCUMENTATION.md)
- **Team Chat**: Contact on internal Slack/Teams
- **Email**: Reach out to project maintainers
- **Office Hours**: Weekly dev sync meetings

## ⚖️ Code of Conduct

- Be respectful and professional
- Provide constructive feedback
- Focus on the code, not the person
- Follow Deloitte's code of conduct
- Maintain confidentiality

## 📄 License

All contributions are subject to Deloitte's proprietary license. By contributing, you agree that your contributions will be owned by Deloitte Consulting LLP.

---

**Thank you for contributing to the ICT Airport Operations Intelligence Platform!**

*Making an impact that matters.*
