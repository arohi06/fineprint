# Fineprint — AI-Powered Privacy Policy Analyzer

**Understand what you're agreeing to before you click "Accept".**

Fineprint is an AI-powered privacy policy analysis application designed to make complex privacy policies easier to understand. It analyzes policy content, identifies potentially concerning clauses, and provides users with a clearer picture of how their data may be collected, processed, and used.

Instead of manually reading lengthy legal documents, users can use Fineprint to get a simplified analysis and identify potential privacy risks.

## Key Features

- **Privacy Policy Analysis:** Analyze privacy policy text to identify potentially concerning content.
- **Machine Learning Classification:** Uses TF-IDF feature extraction and Logistic Regression to classify policy text.
- **Rule-Based Detection:** Combines machine learning predictions with rule-based checks for additional analysis.
- **Negation Handling:** Considers negation patterns to improve the interpretation of policy statements.
- **Risk Assessment:** Generates a risk-oriented analysis using classification results and predefined scoring thresholds.
- **Analysis Interface:** Provides a simple web interface for submitting and viewing policy analysis results.
- **Report Generation:** Generates reports containing the analysis results.

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Machine Learning | Scikit-learn |
| Feature Extraction | TF-IDF |
| Classification | Logistic Regression |
| Database | SQLite |

## Project Architecture

Fineprint follows a frontend-backend architecture.

1. The user submits privacy policy content through the frontend.
2. The backend receives and processes the submitted content.
3. Text preprocessing and feature extraction prepare the content for analysis.
4. The machine learning model classifies the text.
5. Rule-based checks supplement the model's predictions.
6. The analysis results are processed into a risk-oriented assessment.
7. Results are presented through the frontend, with report generation support.

## Installation and Setup

### Prerequisites

- Python 3.10 or above
- pip
- Git

### 1. Clone the repository

```bash
git clone https://github.com/arohi06/fineprint.git
cd fineprint
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

**Option 1 — Using Python:**

```bash
python run.py
```

**Option 2 — Windows:**

```bash
start.bat
```

Follow the terminal output for the application URL and API documentation.

## Machine Learning Approach

Fineprint combines machine learning and rule-based analysis.

**1. Text Processing**

Policy content is processed and converted into numerical features using TF-IDF vectorization with unigram and bigram features.

**2. Machine Learning Classification**

A Logistic Regression classifier is used to identify potentially concerning policy statements based on learned text patterns.

**3. Rule-Based Analysis**

Additional rules and negation handling supplement the model's predictions to improve the overall analysis.

**4. Risk Assessment**

The application combines the analysis signals to produce a risk-oriented assessment.

## Future Improvements

- Support for uploading complete privacy policy documents.
- Improved contextual understanding using transformer-based NLP models.
- More comprehensive privacy clause categorization.
- Explainable AI for highlighting why specific clauses are flagged.
- Support for additional languages.
- Improved analysis reports and visualizations.

## Limitations

- Analysis quality depends on the training data and detection rules.
- Machine learning predictions may not capture every legal or contextual nuance.
- Results are intended for informational purposes and should not be considered legal advice.

## Contributing

Contributions, suggestions, and feedback are welcome.

If you find an issue or have an improvement in mind, feel free to open an issue or submit a pull request.
