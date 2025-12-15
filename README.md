# Full-Stack AI Web Application

A modern full-stack application combining a **Flask backend** and a **React frontend**, designed for AI-powered features and scalable deployment.

---

## 🧠 Features
- Flask REST API
- React frontend
- AI / Machine Learning integration
- Secure authentication-ready architecture
- Clean separation between frontend & backend

---

## 🗂 Project Structure

project-root/
├── backend/
│ ├── app/
│ ├── main.py
│ ├── requirements.txt
│ └── venv/ # ignored
├── frontend/
│ ├── src/
│ ├── public/
│ └── package.json
├── .gitignore
├── .gitattributes
└── README.md
---

## ⚙️ Backend Setup (Flask)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

---

##🎨 Frontend Setup (React)

cd frontend
npm install
npm start

##🚀 Deployment (Planned)

Frontend: Vercel

Backend: Render

Database: MongoDB Atlas

##📌 Author

Nawres BY
Software Engineering & AI Enthusiast


---

# ✅ 4️⃣ Clean Git state (VERY IMPORTANT)

Run these **in order**:

```bash
git rm -r --cached backend/venv
git add .
git commit -m "Clean project structure and add configuration files"


