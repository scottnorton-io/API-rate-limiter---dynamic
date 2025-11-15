# Contributing to `dynamic-api-rate-limiter`

Thank you for considering contributing! 🎉  
This project provides a clean, reliable, dynamic API rate limiter with per-API configurations.

---

## 📦 Getting Started

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/dynamic-api-rate-limiter.git
cd dynamic-api-rate-limiter
```

### 2. Virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -e .
pip install pytest ruff
```

---

## 🧪 Running Checks

### Lint

```bash
ruff check api_ratelimiter examples
```

### Tests

```bash
pytest
```

---

## 🧩 Project Structure

```text
dynamic-api-rate-limiter/
    api_ratelimiter/
        dynamic_ratelimiter.py
        api_rate_config.py
        clients.py
    examples/
        example_notion.py
        example_vanta.py
        example_fieldguide.py
    README.md
    CONTRIBUTING.md
    LICENSE
    pyproject.toml
    background.md
```

---

## 🔁 Pull Request Process

1. Create a feature branch:

```bash
git checkout -b feature/my-feature
```

2. Make changes  
3. Run lint + tests  
4. Commit:

```bash
git commit -am "Add <feature>"
```

5. Push & open PR  
6. Fill out description (what/why/breaking changes)

---

## 🙏 Thanks

Your contributions make the library better for everyone!  
