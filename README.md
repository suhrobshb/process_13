# 🚀 AutoOps - AI-Driven Process Automation Platform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/suhrobshb/process_13)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://www.typescriptlang.org/)

**AutoOps** is a comprehensive, enterprise-grade AI-driven RPA platform that enables users to record, understand, and automate complex desktop and web workflows through an intuitive visual interface with real-time collaboration capabilities.

## ▶️ Quickstart

### 1. Clone & enter project
```bash
git clone https://github.com/suhrobshb/process_13.git
cd process_13
```

### 2. Environment Setup

Create a `.env` file in the project root with the following variables:
```bash
OPENAI_API_KEY=your_openai_api_key
SLACK_TOKEN=your_slack_token  # Optional
TWILIO_ACCOUNT_SID=your_twilio_sid  # Optional
TWILIO_AUTH_TOKEN=your_twilio_token  # Optional
```

### 3. Running with Docker (Recommended)

```bash
# Build and start all services
docker-compose up --build

# To run in detached mode
docker-compose up -d
```

### 4. Running without Docker

#### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- MongoDB 6+
- Redis 7+
- Tesseract OCR

#### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the application
python main.py
```

## 📚 Documentation

Comprehensive documentation is available:
- [🗺️ Implementation Roadmap](IMPLEMENTATION_ROADMAP_CONSOLIDATED.md) - Complete development roadmap
- [📖 User Guide](USER_GUIDE.md) - Complete user manual
- [🧪 Testing Guide](USER_TESTING_GUIDE.md) - Testing instructions
- [🚀 Quick Start](QUICK_START_GUIDE.md) - Getting started guide
- [📊 System Status](FINAL_SYSTEM_STATUS.md) - Current system status
- [🏗️ Architecture](docs/EXECUTION_ARCHITECTURE.md) - System architecture
- [🔗 RAG Integration](docs/RAG_INTEGRATION_GUIDE.md) - RAG system guide

## 🔧 Configuration

The application can be configured through `config/default.yaml`. Key settings include:
- Server configuration
- Database connections
- AI model settings
- Integration settings

## 🚀 Features

### **Core Automation**
- ✅ **Desktop Automation** - PyAutoGUI-based universal desktop control
- ✅ **Browser Automation** - Playwright-powered web automation
- ✅ **AI Learning Engine** - Intent recognition and pattern analysis
- ✅ **Workflow Engine** - Robust step-by-step execution

### **Modern Frontend**
- ✅ **React TypeScript Dashboard** - Modern UI with Tailwind CSS
- ✅ **Real-time Collaboration** - Multi-user editing with WebSocket
- ✅ **Visual Workflow Editor** - Drag-and-drop interface with 15+ node types
- ✅ **Analytics Dashboard** - ROI tracking and performance metrics

### **Enterprise Features**
- ✅ **JWT Authentication** - Secure token-based authentication
- ✅ **Role-Based Access Control** - Granular permission system
- ✅ **Real-time Monitoring** - Live system statistics
- ✅ **Comprehensive Testing** - 70%+ code coverage
- ✅ **Production Ready** - Docker & Kubernetes support

## 🏗️ Architecture

### **Backend Stack**
- **FastAPI** - High-performance API framework
- **SQLModel** - Type-safe database models
- **PostgreSQL** - Production database
- **Redis** - Caching and session management
- **Celery** - Asynchronous task processing
- **WebSocket** - Real-time communication

### **Frontend Stack**
- **React 18** - Modern component framework
- **TypeScript** - Type-safe development
- **Vite** - Fast build tooling
- **Tailwind CSS** - Utility-first styling
- **ReactFlow** - Visual workflow editor
- **React Query** - Data fetching and caching

## 🧪 Testing

```bash
# Run backend tests
python -m pytest ai_engine/tests/ -v

# Run with coverage
python -m pytest ai_engine/tests/ --cov=ai_engine --cov-report=html

# Test specific components
python -m pytest ai_engine/tests/test_workflow_engine.py -v
```

## 🤝 Contributing

1. Fork the repository at [https://github.com/suhrobshb/process_13](https://github.com/suhrobshb/process_13)
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.