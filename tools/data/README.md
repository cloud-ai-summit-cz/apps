# Data Tools

Toy profile data generator and management scripts.

## Contents

- `toy_profiles.json` - AI-generated toy profiles
- `toy-images/` - Avatar images (256x256 JPEG)
- `toy-profile-generator/` - AI generator using Azure OpenAI

## Quick Start

### 1. Generate Toy Profiles

```powershell
cd toy-profile-generator
# Configure .env first (see .env.example)
uv sync
uv run python main.py
```

### 2. Authenticate

```powershell
cd ../../../tools/identity
uv run python get_auth_token.py
```

### 3. Start Toy Service

```powershell
cd ../../src/services/toy
uv run uvicorn main:app --reload --port 8001
```

### 4. Import to Toy Service

```powershell
cd ../../../tools/data
uv sync
uv run python import-toy-profiles.py
```

### 5. Check Imported Toys

```powershell
uv run python check-toy-profiles.py
```

## Scripts

### Import Toy Profiles

```powershell
uv run python import-toy-profiles.py
```

### Check Imported Toys

```powershell
uv run python check-toy-profiles.py
```

### Clean All Toys

```powershell
uv run python clean-toy-profiles.py
```

## Configuration

Copy `.env.example` to `.env` and configure:
- `TOY_SERVICE_URL` - Service endpoint
- `AUTH_TOKEN_PATH` - Path to auth token JSON
