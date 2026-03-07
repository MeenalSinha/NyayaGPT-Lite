# Dataset Directory

Training data for NyayaGPT Lite model fine-tuning.

## Files

- `sample.json` - Basic sample data structure
- `sample_training_data.json` - Complete training examples (4 examples)

## Dataset Format

Each training example follows this structure:

```json
{
  "id": "unique_identifier",
  "instruction": "Task description in natural language",
  "input": "The legal document text to explain",
  "output": "Structured explanation in simple language",
  "metadata": {
    "document_type": "FIR|COURT_ORDER|LEGAL_NOTICE",
    "language": "english|hindi",
    "case_category": "fraud|civil|criminal|property|family",
    "complexity": "simple|medium|complex",
    "sections": ["IPC 420", "IPC 406"]
  }
}
```

## Usage

### For Training:

Load in Kaggle notebook:
```python
from datasets import load_dataset
dataset = load_dataset('json', data_files='sample_training_data.json')
```

### Creating More Data:

Follow the guide in `docs/DATASET_PREPARATION.md`

Minimum recommended: 300 examples
Optimal: 800-1000 examples

### Distribution:

- 70% Training
- 15% Validation  
- 15% Test

## Data Sources

- Public court judgments (anonymized)
- Legal aid materials
- Synthetic examples
- Sample documents

**Important:** Always anonymize personal information!

## Quality Guidelines

Each example should:
- Be at least 100 words (input)
- Have structured output with all sections
- Use simple, clear language
- Not provide legal advice
- Not predict outcomes
- Be legally accurate

See `docs/DATASET_PREPARATION.md` for details.
