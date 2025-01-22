# Invoice Payment Agent Backend

An intelligent multi-agent system that automates invoice processing and payments using AI. The system processes emails with PDF invoices, extracts information using Composio AI, and handles payments through secure payment gateways.

## Features

- 📧 **Email Integration**: Automatically fetches and processes emails with invoice attachments
- 📎 **PDF Processing**: Downloads and stores PDF attachments securely
- 🤖 **AI-Powered Extraction**: Uses Composio AI for accurate invoice data extraction
- 💰 **Payment Processing**: Automates payment processing with validation
- 📊 **History Tracking**: Maintains detailed payment and processing history
- 🔒 **Security**: Implements secure credential management and data handling

## System Architecture

### Agent System

1. **Multi Agent** (`src/agents/multi_agent.py`)
   - Orchestrates communication between specialized agents
   - Manages workflow and error handling
   - Coordinates parallel processing tasks

2. **Email Agent** (`src/agents/email_agent.py`)
   - Gmail API integration for email fetching
   - Email filtering and attachment handling
   - Secure credential management

3. **PDF Agent** (`src/agents/pdf_agent.py`)
   - PDF download and storage management
   - Integration with Composio AI for text extraction
   - PDF validation and error handling

4. **Payment Agent** (`src/agents/payment_agent.py`)
   - Payment processing and validation
   - Payment gateway integration
   - Transaction history management

### Tools and Utilities

1. **Email Tools** (`src/tools/email_tools.py`)
   - Email processing utilities
   - MIME handling
   - Attachment extraction

2. **Payment Tools** (`src/tools/payment_tools.py`)
   - Payment validation
   - Currency handling
   - Payment gateway interfaces

3. **Shared Tools** (`src/tools/shared_tools.py`)
   - Common utilities
   - Data validation
   - Error handling

## Setup Instructions

### Prerequisites

- Python 3.8+
- Virtual environment
- Gmail API credentials
- Composio API key
- Payment gateway credentials

### Installation

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd backend
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   ```
   

## Directory Structure

```
backend/
├── src/
│   ├── agents/           # Agent implementations
│   ├── tools/            # Utility functions
│   ├── invoice data/     # Data storage
│   └── scripts/          # Test scripts
├── reference/            # Documentation
└── venv/                # Virtual environment
```

## Configuration

### Email Settings

```python
EMAIL_CONFIG = {
    'query': 'has:attachment newer_than:7d',
    'max_results': 10,
    'attachment_dir': 'invoice data/email_attachments'
}
```

### Payment Processing

Using Payman to process payments.

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest src/scripts/test_invoice_processor.py
```

### Adding New Features

1. **New Agent Implementation**
   - Create new agent in `src/agents/`
   - Implement required interfaces
   - Add to multi-agent system

2. **New Payment Gateway**
   - Add gateway interface in `src/tools/payment_tools.py`
   - Implement required methods
   - Update configuration

## Troubleshooting

### Common Issues

1. **Email Authentication**
   - Verify Gmail API credentials
   - Check refresh token validity
   - Confirm API permissions

2. **Composio Integration**
   - Validate API key
   - Check rate limits
   - Review extraction templates

3. **Payment Processing**
   - Verify payment gateway credentials
   - Check transaction logs
   - Validate payment data

## Contributing

1. Fork the repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## License

MIT License - see LICENSE file for details. 