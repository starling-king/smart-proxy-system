# Use Python 3.11-slim (Matches your project version)
FROM python:3.11-slim

# Set working directory to /app
WORKDIR /app

# --- [FEATURE 1] Optimization & Live Logging ---
# Prevents Python from writing .pyc files (Faster startup)
ENV PYTHONDONTWRITEBYTECODE=1
# Critical: Ensures logs print immediately to your Docker console
ENV PYTHONUNBUFFERED=1

# --- [FEATURE 2] System Stability ---
# Installs gcc to ensure Pandas/Numpy install correctly on Linux
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --- [FEATURE 3] Optimized Dependencies ---
# We COPY from root (.) because you cleaned up requirements.txt there
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy Project Files ---
COPY . .

# --- [FEATURE 4] Crash Prevention ---
# Pre-creates data folders so setup_test_data.py never fails on permission/missing dir errors
RUN mkdir -p data/Teacher_Timetables data/Absent_Lists

# --- [FEATURE 5] Correct Import Paths ---
# Critical: Adds 'backend' to Python path so "from api..." imports work anywhere
ENV PYTHONPATH=/app/backend

# --- Port Documentation ---
EXPOSE 5000

# --- [FEATURE 6] The "Brain" Execution Chain ---
# 1. Runs Setup (Generates Saturday's Timetable)
# 2. Runs Tests (Ensures Logic is sound)
# 3. Starts App (Launches Website)
# Uses JSON format ["sh", "-c"] to satisfy VS Code and Docker best practices
CMD ["sh", "-c", "python backend/setup_test_data.py && python -m pytest backend/tests -p no:warnings && python backend/app.py"]