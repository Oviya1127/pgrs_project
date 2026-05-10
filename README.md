
# SPGRS – Smart Public Grievance Redressal System

## Project Overview

SPGRS (Smart Public Grievance Redressal System) is a production-ready web application developed to streamline the grievance registration, tracking, and resolution process for citizens and administrative departments.

The system provides separate portals for citizens and administrators, enabling transparent grievance management, secure authentication, role-based access control, and efficient complaint resolution workflows.

The application is built using a modern backend architecture with FastAPI and PostgreSQL, along with lightweight static frontend interfaces using HTML, CSS, and JavaScript.

---

# Key Features

* Citizen grievance registration and tracking
* Secure JWT-based authentication and authorization
* Role-based access control for administrators and users
* Complaint categorization and department assignment
* File attachment support using Cloudinary
* Admin dashboard for grievance management
* RESTful API architecture using FastAPI
* PostgreSQL database integration with async support
* Production-ready project structure
* Static frontend deployment support
* Environment-based configuration using `.env`

---

# Technology Stack

| Layer             | Technology            |
| ----------------- | --------------------- |
| Backend Framework | FastAPI               |
| ASGI Server       | Uvicorn               |
| Database          | PostgreSQL            |
| Database Driver   | asyncpg               |
| Authentication    | JWT (python-jose)     |
| Password Hashing  | bcrypt (passlib)      |
| Configuration     | Pydantic Settings     |
| File Storage      | Cloudinary            |
| Frontend          | HTML, CSS, JavaScript |

---

# Project Structure

```text
pgrs_project/
│
├── config/
│   └── settings.py
│
├── backend/
│   ├── app.py
│   ├── middleware/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
├── frontend/
│   ├── assets/
│   ├── admin/
│   └── user/
│
├── scripts/
│
├── .env.example
├── create_database.py
├── create_new_admin.py
├── seed.py
├── run.py
└── requirements.txt
```

---

# System Modules

## User Module

* User registration and login
* Submit grievances
* Track complaint status
* Upload supporting documents
* View grievance history

## Admin Module

* Secure administrator login
* View and manage grievances
* Update grievance status
* Assign grievances to departments
* Monitor complaint resolution process

---

# Installation and Setup

## Step 1 – Create Virtual Environment

```bash
python -m venv venv
```

Activate virtual environment:

### Windows

```bash
.\venv\Scripts\activate.bat
```

### Linux / MacOS

```bash
source venv/bin/activate
```

---

## Step 2 – Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 3 – Configure Environment Variables

Copy `.env.example` to `.env` and configure the following:

```env
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=

SECRET_KEY=

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

---

## Step 4 – Database Setup

Run the following scripts in order:

```bash
python create_database.py
python create_new_admin.py
python seed.py
```

### Script Descriptions

| Script              | Purpose                               |
| ------------------- | ------------------------------------- |
| create_database.py  | Creates database schema and seed data |
| create_new_admin.py | Creates or updates default admin      |
| seed.py             | Inserts sample user data              |
| run.py              | Starts application servers            |

---

# Running the Application

Start the application using:

```bash
python run.py
```

---

# Application URLs

| Service           | URL                                                                                                        |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| User Portal       | [http://localhost:8000](http://localhost:8000)                                                             |
| User Login        | [http://localhost:8000/static/user/user_login.html](http://localhost:8000/static/user/user_login.html)     |
| API Documentation | [http://localhost:8000/docs](http://localhost:8000/docs)                                                   |
| Admin Portal      | [http://localhost:8001](http://localhost:8001)                                                             |
| Admin Login       | [http://localhost:8001/static/admin/admin_login.html](http://localhost:8001/static/admin/admin_login.html) |

---

# Default Credentials

## Administrator Account

```text
Email    : sara_admin@gmail.com
Password : admin123
```

## Test User Account

```text
Email    : testing@gmail.com
Password : testing123
```

## Citizen Account

```text
Email    : citizen@spgrs.com
Password : user123
```

---

# Security Features

* JWT token authentication
* Password hashing using bcrypt
* Environment variable protection
* Role-based authorization
* Configurable CORS support
* Secure API routing

---

# Production Deployment Recommendations

* Use a strong `SECRET_KEY`
* Restrict CORS origins in production
* Deploy behind Nginx reverse proxy
* Enable HTTPS using SSL certificates
* Use Docker and Kubernetes for scalable deployment
* Keep `.env` excluded from version control
* Run services using process managers such as systemd or Docker Compose

---

# Future Enhancements

* Email and SMS notifications
* Real-time grievance tracking
* Analytics dashboard
* Department performance reports
* Mobile application integration
* Multi-language support
* AI-based grievance categorization

---

# Conclusion

SPGRS provides a scalable and secure platform for managing public grievances efficiently. The system is designed with modular architecture, production-ready deployment practices, and modern backend technologies to support reliable grievance handling and administrative workflows.

---

# Developed By

**OVIYA**
Smart Public Grievance Redressal System
FastAPI • PostgreSQL • Docker • Kubernetes • CI/CD


# DevOps Deployment Guide – SPGRS Project

## Overview

This document contains the DevOps setup, Dockerization, CI/CD workflow, Kubernetes deployment steps, and essential commands required to deploy the SPGRS (Smart Public Grievance Redressal System) application in a production-like environment.

---

# DevOps Technology Stack

| Component               | Technology           |
| ----------------------- | -------------------- |
| Containerization        | Docker               |
| Container Orchestration | Kubernetes           |
| CI/CD                   | GitHub Actions       |
| Reverse Proxy           | Nginx                |
| Backend                 | FastAPI              |
| Database                | PostgreSQL           |
| Monitoring (Optional)   | Prometheus & Grafana |
| Logging (Optional)      | Loki / ELK Stack     |

---

# Project Deployment Architecture

```text id="wzokp5"
Developer Push
       ↓
GitHub Repository
       ↓
GitHub Actions CI/CD
       ↓
Docker Image Build
       ↓
Docker Hub Push
       ↓
Kubernetes Deployment
       ↓
Nginx Reverse Proxy
       ↓
SPGRS Application
```

---

# Docker Setup

## 1. Build Docker Image

```bash id="t7u6v8"
docker build -t spgrs-app .
```

---

## 2. Run Docker Container

```bash id="l6n1fg"
docker run -d -p 8000:8000 --name spgrs-container spgrs-app
```

---

## 3. View Running Containers

```bash id="w9l3ya"
docker ps
```

---

## 4. View All Containers

```bash id="vfrw9m"
docker ps -a
```

---

## 5. Stop Container

```bash id="pc3zqf"
docker stop spgrs-container
```

---

## 6. Remove Container

```bash id="ovq8nx"
docker rm spgrs-container
```

---

## 7. Remove Docker Image

```bash id="ewbrk2"
docker rmi spgrs-app
```

---

# Docker Compose Setup

## Run Application Using Docker Compose

```bash id="0b4g8r"
docker-compose up -d
```

---

## Stop Docker Compose Services

```bash id="2h7m1w"
docker-compose down
```

---

# Kubernetes Deployment

## 1. Apply Deployment YAML

```bash id="qlzj0o"
kubectl apply -f deployment.yaml
```

---

## 2. Apply Service YAML

```bash id="zjlwm2"
kubectl apply -f service.yaml
```

---

## 3. View Pods

```bash id="1r0vkk"
kubectl get pods
```

---

## 4. View Deployments

```bash id="m7xvvv"
kubectl get deployments
```

---

## 5. View Services

```bash id="ww3c2i"
kubectl get services
```

---

## 6. Describe Pod

```bash id="o3vxlj"
kubectl describe pod <pod-name>
```

---

## 7. View Pod Logs

```bash id="58w5vj"
kubectl logs <pod-name>
```

---

## 8. Execute Shell Inside Pod

```bash id="e2m8e1"
kubectl exec -it <pod-name> -- sh
```

---

## 9. Delete Deployment

```bash id="ndzj8v"
kubectl delete deployment spgrs-deployment
```

---

# Nginx Reverse Proxy Configuration

## Sample Nginx Configuration

```nginx id="i53l7m"
server {
    listen 80;

    location / {
        proxy_pass http://localhost:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Restart Nginx

### Linux

```bash id="ksv07w"
sudo systemctl restart nginx
```

---

# GitHub Actions CI/CD Pipeline

## CI/CD Workflow Steps

1. Developer pushes code to GitHub
2. GitHub Actions workflow triggers automatically
3. Docker image is built
4. Image is pushed to Docker Hub
5. Kubernetes deployment is updated

---

## Sample GitHub Actions Workflow

```yaml id="h0m92m"
name: SPGRS CI/CD Pipeline

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Source
        uses: actions/checkout@v3

      - name: Login to Docker Hub
        run: docker login -u ${{ secrets.DOCKER_USERNAME }} -p ${{ secrets.DOCKER_PASSWORD }}

      - name: Build Docker Image
        run: docker build -t spgrs-app .

      - name: Tag Docker Image
        run: docker tag spgrs-app username/spgrs-app:latest

      - name: Push Docker Image
        run: docker push username/spgrs-app:latest
```

---

# PostgreSQL Commands

## Connect to PostgreSQL

```bash id="3ptkh9"
psql -U postgres
```

---

## Create Database

```sql id="8v0sc1"
CREATE DATABASE spgrs_db;
```

---

## List Databases

```sql id="b4m2kv"
\l
```

---

# Docker Commands

| Command                           | Purpose                        |
| --------------------------------- | ------------------------------ |
| docker images                     | View Docker images             |
| docker logs container_name        | View container logs            |
| docker exec -it container_name sh | Open container shell           |
| docker system prune -a            | Remove unused Docker resources |

---

# Kubernetes Commands

| Command                                            | Purpose            |
| -------------------------------------------------- | ------------------ |
| kubectl get pods                                   | View running pods  |
| kubectl get svc                                    | View services      |
| kubectl get deployments                            | View deployments   |
| kubectl logs pod-name                              | View pod logs      |
| kubectl delete pod pod-name                        | Delete pod         |
| kubectl rollout restart deployment deployment-name | Restart deployment |

---

# Deployment Workflow

```text id="tzb2jc"
Code Development
       ↓
Git Push to GitHub
       ↓
GitHub Actions Triggered
       ↓
Docker Image Build
       ↓
Push Image to Docker Hub
       ↓
Kubernetes Pulls Image
       ↓
Application Deployment
       ↓
Nginx Reverse Proxy
       ↓
Public Access
```

