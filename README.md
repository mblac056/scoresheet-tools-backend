# Scoresheet Parser Backend

A Python-based service that converts barbershop competition scoresheet PDFs into various formats (CSV, JSON, and pivot table format). This service runs as an AWS Lambda function and processes PDFs using tabula-py for table extraction.

## Features

- PDF to CSV conversion
- PDF to JSON conversion with structured data
- Pivot table format generation
- AWS Lambda integration
- Docker containerization

## Prerequisites

- Python 3.11+
- Docker
- AWS CLI (for deployment)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mblac056/scoresheet-tools-backend.git
cd scoresheet-parser-backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Local Development

The parser can be used locally with the following command:

```bash
python parser.py --input path/to/scoresheet.pdf --formats csv json pivot
```

Available formats:
- `csv`: Raw table data
- `json`: Structured data with group and round information
- `pivot`: Pivot table format for analysis

### AWS Lambda

The service is designed to run as an AWS Lambda function. The `lambda_handler.py` file contains the entry point for Lambda invocations.

## Project Structure

```
backend/
├── app.py              # Flask application (if needed)
├── lambda_handler.py   # AWS Lambda entry point
├── parser.py          # Main parsing logic
├── requirements.txt   # Python dependencies
└── Dockerfile        # Container definition
```

## API Documentation

### Lambda Function Input

The Lambda function expects a JSON input with the following structure:

```json
{
    "pdf_url": "https://example.com/scoresheet.pdf",
    "formats": ["csv", "json", "pivot"]
}
```

### Lambda Function Output

The function returns a JSON response with URLs to the generated files:

```json
{
    "csv_url": "https://example.com/output.csv",
    "json_url": "https://example.com/output.json",
    "pivot_url": "https://example.com/output_pivot.csv"
}
```

## Development

### Local Testing

1. Build the Docker image:
```bash
docker build -t scoresheet-server .
```

2. Run tests (when implemented):
```bash
python -m pytest
```

### Deployment

The service is deployed as a Docker container to AWS Lambda. See the deployment documentation for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [tabula-py](https://github.com/chezou/tabula-py) for PDF table extraction
- AWS Lambda for serverless execution 