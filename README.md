# 🎓 Smart Proxy Management System

A structured and automated system for managing academic proxy (substitution) lectures.

---

## 🧠 Purpose

This system replaces manual substitution management with a transparent and automated dashboard.

Core principles:

- ✅ Race-condition safe claim system  
- ✅ Timezone aware (India Standard Time)  
- ✅ CSV-based lightweight database  
- ✅ Zero external database dependency  

---

## 🖥️ Environment Information

- **Python Version:** 3.13  
- **Tested On:** Windows 11  
- **Framework:** Flask  
- **Data Handling:** Pandas  

---

# 🚀 How to Run (Without Docker – Recommended)

If Docker is not working properly, follow this method.

---

## Step 1: Install Python

Verify Python is installed:

```bash
python --version
````

It should show:

```
Python 3.13.x
```

---

## Step 2: Install Dependencies

Inside the project root folder, run:

```bash
pip install -r requirements.txt
```

This installs all required packages.

---

## Step 3: Run Tests (Recommended)

Before running the system, verify integrity:

```bash
pytest
```

All tests should pass before proceeding.

---

## Step 4: Start the Application

```bash
python backend/app.py
```

Now open your browser:

```
http://localhost:5000
```

---

# 📂 Test Data Usage

The project already contains sample timetable and absence data.

You can modify:

```
data/Teacher_Timetables/
data/Absent_Lists/
```

---

## ⚠️ Important Rule for Timetable CSV

The CSV structure must remain exactly:

```
Day,Time,Department,ClassOrLab,Subject,TeacherKey
```

* Do not change column names.
* TeacherKey must match the teacher’s name.
* Filename should represent the teacher.

Example:

```
Amit_Timetable.csv
raj.csv
rohit.csv
```

If structure changes, the system will fail.

---

# 🐳 Docker (Optional – If Working)

## Build:

```bash
docker build -t proxy-app .
```

## Run:

```bash
docker run -p 5000:5000 --name proxy-demo --rm proxy-app
```

Then open:

```
http://localhost:5000
```

---

# 🧪 For Custom Testing

1. Edit absent list file.
2. Modify timetable CSV.
3. Restart the server.
4. System recalculates automatically.

---

# 📁 Project Structure

```
PROXY_APP/
├── backend/
│   ├── app.py
│   ├── proxy_core.py
│   ├── setup_test_data.py
│   └── tests/
├── frontend/
├── data/
├── Dockerfile
└── requirements.txt
```

---

## ✅ Recommendation

Always run `pytest` before demo or submission to ensure system stability.

```

---

Now important part:

After editing README.md:

Run:

```

git add README.md
git commit -m "Updated README with Python 3.13 instructions"
git push

```

That ensures GitHub shows the updated version.

---

Small but important observation:

Python 3.13 is very new.  
Some libraries may not fully support it yet.

If anything breaks in professor’s system,  
Python 3.11 is currently more stable.

Think strategically.

Do you want maximum stability or latest version branding?

Be intentional.
```
