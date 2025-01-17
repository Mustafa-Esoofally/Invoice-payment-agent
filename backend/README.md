# Invoice Payment Agent

An automated system that processes invoice payments by fetching emails with PDF attachments, extracting invoice information, and processing payments.

## Features

- 📧 **Email Integration**: Automatically fetches emails with attachments
- 📎 **Attachment Handling**: Downloads and processes PDF attachments
- 📄 **PDF Processing**: Extracts text and structured data from PDF invoices
- 💰 **Payment Processing**: Processes payments based on extracted invoice data
- 🤖 **Multi-Agent System**: Coordinates between different specialized agents
- 🔍 **Flexible Extraction**: Handles various invoice formats and layouts

## System Components

1. **Email Agent** (`email_agent.py`)
   - Fetches emails with attachments
   - Filters based on query parameters
   - Handles Gmail API integration

2. **Attachment Agent** (`attachment_agent.py`)
   - Downloads email attachments
   - Manages file storage
   - Handles different attachment types

3. **PDF Extraction Agent** (`pdf_extraction_agent.py`)
   - Extracts text from PDF files
   - Processes multi-page documents
   - Provides structured text output

4. **Payment Agent** (`payment_agent.py`)
   - Processes payments
   - Validates payment information
   - Handles payment API integration

5. **Invoice Payment Processor** (`invoice_payment_processor.py`)
   - Extracts invoice information
   - Validates extracted data
   - Prepares payment requests

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)
- Gmail API access
- Composio API key
- Payment API credentials

### Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd invoice-payment-agent
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   ```bash
   # Copy example configuration
   cp .env.example .env

   # Edit .env file with your credentials
   # Required variables:
   # - COMPOSIO_API_KEY
   # - GMAIL_API_CREDENTIALS
   # - PAYMENT_API_KEY
   ```

### Usage

1. **Basic Usage**
   ```python
   # Run the complete workflow
   python workflow_test.py
   ```

2. **Individual Components**
   ```python
   # Email fetching only
   python email_agent.py

   # PDF processing only
   python pdf_extraction_agent.py

   # Payment processing only
   python payment_agent.py
   ```

## Configuration

### Email Settings
- `query`: Email search query (default: "has:attachment newer_than:7d")
- `max_results`: Maximum number of emails to fetch (default: 10)

### PDF Processing
- `download_dir`: Directory for downloaded attachments (default: "downloads")
- `debug`: Enable debug output (default: True)

### Payment Processing
- `currency`: Default currency for payments (default: "USD")
- `batch_size`: Maximum payments per batch (default: 10)

## Error Handling

The system includes comprehensive error handling for:
- Invalid email attachments
- PDF extraction failures
- Payment processing errors
- API connection issues

## Development

### Project Structure
```
invoice-payment-agent/
├── email_agent.py         # Email fetching
├── attachment_agent.py    # Attachment handling
├── pdf_extraction_agent.py # PDF processing
├── payment_agent.py       # Payment processing
├── payment_tools.py       # Payment utilities
├── invoice_payment_processor.py # Invoice processing
├── multi_agent.py         # Agent coordination
├── email_pdf_processor.py # Email-PDF integration
├── workflow_test.py       # Complete workflow test
├── .env                   # Configuration
└── requirements.txt       # Dependencies
```

### Adding New Features

1. **New Invoice Formats**
   - Add patterns to `invoice_payment_processor.py`
   - Update validation rules as needed

2. **Additional Payment Methods**
   - Add new payment tools to `payment_tools.py`
   - Update payment agent configuration

3. **Custom Processing**
   - Extend relevant agent classes
   - Add new processing methods as needed

## Troubleshooting

### Common Issues

1. **Email Fetching Fails**
   - Check Gmail API credentials
   - Verify email query syntax
   - Ensure proper authentication

2. **PDF Extraction Issues**
   - Verify PDF file format
   - Check file permissions
   - Enable debug mode for detailed logs

3. **Payment Processing Errors**
   - Verify payment API credentials
   - Check payment data format
   - Review error logs

### Debug Mode

Enable debug mode in each component for detailed logging:
```python
agent = EmailAgent(debug=True)
processor = InvoicePaymentProcessor(debug=True)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 