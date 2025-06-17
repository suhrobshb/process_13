# AutoOps

**AutoOps** is an AI-driven RPA platform to record, understand, and automate desktop/web workflows.

## ▶️ Quickstart

### 1. Clone & enter project
```bash
git clone https://your.repo/auto-ops-final.git
cd auto-ops-final

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

Detailed documentation is available in the `docs/` directory:
- [Architecture Overview](docs/architecture.md)
- [API Documentation](docs/api.md)
- [User Guide](docs/user-guide.md)

## 🔧 Configuration

The application can be configured through `config/default.yaml`. Key settings include:
- Server configuration
- Database connections
- AI model settings
- Integration settings

## 🚀 Features

- AI-powered workflow automation
- Desktop and web automation
- Natural language processing
- Integration with popular services
- Real-time monitoring and analytics

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.