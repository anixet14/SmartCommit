# AI Git Commit Message Writer

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%20API-orange.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An intelligent Git hook that automatically generates high-quality, Conventional Commits-formatted commit messages using Google's Gemini AI. Never write commit messages manually again!

## 📋 Description

This project provides a `prepare-commit-msg` Git hook that analyzes your staged changes and uses Google Gemini AI to generate meaningful, well-structured commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) format. It runs automatically before your commit editor opens, pre-populating it with an AI-generated message that you can accept, edit, or reject.

## ✨ Features

- **🤖 AI-Powered**: Leverages Google Gemini 2.5 Flash model for intelligent commit message generation
- **📝 Conventional Commits**: Generates messages following industry-standard format (feat, fix, chore, etc.)
- **🔄 Smart Retry Logic**: Automatically retries on transient API errors with exponential backoff
- **🎯 Context-Aware**: Analyzes actual git diff to generate accurate, relevant messages
- **⚡ Non-Blocking**: Gracefully skips AI generation on API failures to never block your commits
- **🌍 Global Setup**: Install once, use across all your Git repositories
- **🧪 Dry-Run Mode**: Test message generation without committing
- **🔒 Secure**: Uses environment variables for API key management
- **📏 Subject Line Enforcement**: Automatically enforces 50-character limit for subject lines

## 🎯 Advantages

- **Save Time**: No more thinking about how to phrase commit messages
- **Consistency**: All commit messages follow the same professional format
- **Better History**: Clear, descriptive commit messages improve project maintainability
- **Learn Best Practices**: See how AI structures commits and learn from it
- **Flexibility**: Works with or without project-specific `.env` files
- **Cross-Platform**: Works on Windows, Linux, and macOS

## 🔧 How It Works

1. **You stage changes**: `git add <files>`
2. **You run commit**: `git commit`
3. **Hook activates**: The `prepare-commit-msg` hook runs automatically
4. **AI analyzes diff**: Gemini examines your staged changes
5. **Message generated**: AI creates a Conventional Commits message
6. **Editor opens**: Pre-filled with the AI-generated message
7. **You review**: Accept as-is, edit, or replace completely

**Example Generated Message:**
```
feat(auth): add JWT token validation

Implement middleware to validate JWT tokens for protected routes.
Add error handling for expired and invalid tokens.
```

## 📦 Installation & Setup

### Prerequisites

- **Git** (2.9 or higher)
- **Python** (3.8 or higher)
- **Google Gemini API Key** ([Get one free here](https://aistudio.google.com/app/apikey))

### Step 1: Clone the Repository

```bash
git clone https://github.com/MiteshJain8/ai-git-commit-message-writer.git
cd ai-git-commit-message-writer
```

### Step 2: Install Python Dependencies

**Option A: Global Installation (Recommended for hook usage)**
```bash
pip install --user google-genai python-dotenv
```

**Option B: Virtual Environment (For development)**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Set Up Your API Key

**Option A: System Environment Variable (Recommended for global hook)**

**Windows:**
```powershell
# PowerShell (permanent)
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your-api-key-here', 'User')

# Or use GUI: Search "Environment Variables" → New → Name: GEMINI_API_KEY
```

**Linux/macOS:**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Option B: Project-Specific `.env` File**
```bash
# Create .env file in project root
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

### Step 4: Configure the Hook

**Option A: Global Setup (All Repositories)**

This makes the hook work in every Git repository on your machine.

**Windows (Git Bash):**
```bash
# Find your system Python path
which python  # Note the output (e.g., /c/Python312/python)

# Create global hooks directory
mkdir -p ~/.git-hooks

# Copy and configure the hook
cp scripts/prepare-commit-msg.py ~/.git-hooks/prepare-commit-msg
chmod +x ~/.git-hooks/prepare-commit-msg

# Edit the shebang in ~/.git-hooks/prepare-commit-msg to match your Python path
# For example: #!/c/Python312/python

# Set global hooks path
git config --global core.hooksPath ~/.git-hooks
```

**Linux/macOS:**
```bash
# Find your system Python path
which python3  # Note the output (e.g., /usr/bin/python3)

# Create global hooks directory
mkdir -p ~/.git-hooks

# Copy and configure the hook
cp scripts/prepare-commit-msg.py ~/.git-hooks/prepare-commit-msg
chmod +x ~/.git-hooks/prepare-commit-msg

# Edit the shebang to match your Python path
# For example: #!/usr/bin/python3

# Set global hooks path
git config --global core.hooksPath ~/.git-hooks
```

**Option B: Single Repository Setup**

```bash
# Copy hook to .git/hooks in your project
cp scripts/prepare-commit-msg.py .git/hooks/prepare-commit-msg
chmod +x .git/hooks/prepare-commit-msg

# Update shebang to point to your Python executable
```

### Step 5: Verify Installation

```bash
# Test with dry-run mode
python scripts/prepare-commit-msg.py .git/COMMIT_EDITMSG --dry-run

# Make a test commit
echo "test" > test.txt
git add test.txt
git commit
# The editor should open with an AI-generated message!
```

## 🧪 Testing

**Dry-Run Mode** (generates message without committing):
```bash
# Stage some changes first
git add <files>

# Preview the generated message
python scripts/prepare-commit-msg.py .git/COMMIT_EDITMSG --dry-run
```

**Unit Tests** (if available):
```bash
python -m unittest discover tests
```

## 🔧 Configuration

You can customize the hook by editing `scripts/prepare-commit-msg.py`:

- **`MODEL_NAME`**: Change the Gemini model (default: `gemini-2.5-flash`)
- **`MAX_SUBJECT_LENGTH`**: Adjust subject line length limit (default: 50)
- **Retry logic**: Modify `max_attempts` in `run_hook()` function

## 🚫 Disabling the Hook

**Temporarily (single commit):**
```bash
git commit --no-verify
```

**For a specific repository:**
```bash
git config core.hooksPath .git/hooks
```

**Globally:**
```bash
git config --global --unset core.hooksPath
```

## 🛠️ Troubleshooting

**Hook not running:**
- Verify hook is executable: `ls -la ~/.git-hooks/prepare-commit-msg`
- Check global hooks path: `git config --global core.hooksPath`
- Ensure shebang points to correct Python: `head -1 ~/.git-hooks/prepare-commit-msg`

**API errors:**
- Verify API key: `echo $GEMINI_API_KEY` (Linux/macOS) or `echo %GEMINI_API_KEY%` (Windows)
- Check API quota at [Google AI Studio](https://aistudio.google.com/)
- Wait a few minutes if you see "503 UNAVAILABLE" (API overloaded)

**Import errors:**
- Ensure `google-genai` is installed globally: `pip list | grep google-genai`
- Check Python version matches shebang: `python --version`

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

- [Google Gemini API](https://ai.google.dev/) for powering the AI generation
- [Conventional Commits](https://www.conventionalcommits.org/) for the commit message format standard

---

**Star ⭐ this repository if you find it helpful!**
