# 🎓 Smart Proxy Management System

### A Robust, Truthful, and Automated Solution for Academic Substitution
**Efficiency. Integrity. Resilience.**

---

## 📖 The Purpose 
This system brings **truth and order** to the chaotic process of assigning "Proxy" (Substitution) lectures. Instead of manual paper sheets or verbal agreements, teachers use a transparent, real-time digital dashboard to claim free slots.

It is built on **Integrity**:
* **Race Condition Safe:** Prevents two teachers from claiming the same slot at the same time using atomic verification.
* **Timezone Intelligent:** Automatically detects "Today" (India Standard Time), ensuring the timetable is always correct, even if the server is in a different time zone.
* **Zero-Dependency:** Uses a portable, crash-proof CSV database that works instantly on any computer.

---

## 🛠️ Prerequisites (Before You Start)
* **Docker Desktop:** Make sure Docker is installed and running on your computer.
* **Project Folder:** Ensure you have this folder unzipped on your desktop.

---

## 🏁 How to Run (Step-by-Step for Beginners)

Follow these exact steps to present this project in class.

### Step 1: Prepare the System ("Build")
*This step installs all the necessary libraries (like Python, Pandas, Flask) inside a secure container. You only need to do this once.*

1.  Open **VS Code** or a **Terminal** inside the project folder.
2.  Copy and paste this command:
    ```bash
    docker build -t proxy-app .
    ```
3.  **What to look for:** You will see lines of text scrolling. Wait until it stops. If you see "Successfully tagged proxy-app", you are ready!

### Step 2: Run the Demo ("Start")
*This starts the website. It automatically generates fresh test data for "Today" so your demo never fails.*

1.  Copy and paste this command:
    ```bash
    docker run -p 5000:5000 --name my-proxy-demo --rm proxy-app
    ```
2.  **What to look for:** You will see a message saying: `SYSTEM READY: Open your browser`.
3.  **Open the Website:** Go to Google Chrome and type: `http://localhost:5000`
4.  **How to Stop:** When finished, go back to the terminal and press `Ctrl + C`.

### Step 3: The "Live Edit" Mode (Advanced)
*Use this ONLY if you want to show the professor that you can edit Excel files on the computer and update the website instantly.*

**For Windows Command Prompt:**
```cmd
docker run -p 5000:5000 --name proxy-demo --rm -v "%cd%/data":/app/data proxy-app


PROXY_APP/
├── backend/
│   ├── app.py              # The Web Server (Flask)
│   ├── proxy_core.py       # The Logic Engine
│   ├── setup_test_data.py  # The Data Generator
│   └── tests/              # Safety Checks
├── frontend/               # User Interface (HTML/CSS/JS)
├── data/                   # Database Storage (CSVs)
├── Dockerfile              # Container Configuration
└── start.sh                # Startup Script