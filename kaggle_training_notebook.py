"""
NyayaGPT Lite - Model Fine-Tuning Notebook
Fine-tune Mistral-7B for legal document explanation

Run this in Kaggle Notebook with GPU enabled (P100 or T4)
"""

# ============================================================================
# SETUP & INSTALLATION
# ============================================================================

# Install required packages
!pip install -q transformers==4.35.2
!pip install -q peft==0.7.1
!pip install -q bitsandbytes==0.41.3
!pip install -q accelerate==0.25.0
!pip install -q datasets==2.15.0
!pip install -q trl==0.7.4

# ============================================================================
# IMPORTS
# ============================================================================

import torch
import json
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    pipeline
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    PeftModel
)
from datasets import Dataset, load_dataset
from trl import SFTTrainer
import warnings
warnings.filterwarnings('ignore')

print("✓ All packages imported successfully")
print(f"✓ PyTorch version: {torch.__version__}")
print(f"✓ CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✓ GPU: {torch.cuda.get_device_name(0)}")

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Model Configuration
    BASE_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
    
    # Training Configuration
    OUTPUT_DIR = "./nyayagpt-mistral-lora"
    NUM_EPOCHS = 3
    BATCH_SIZE = 4
    GRADIENT_ACCUMULATION_STEPS = 4
    LEARNING_RATE = 2e-4
    MAX_SEQ_LENGTH = 2048
    
    # LoRA Configuration
    LORA_R = 16
    LORA_ALPHA = 32
    LORA_DROPOUT = 0.05
    
    # Quantization
    USE_4BIT = True
    BNB_4BIT_COMPUTE_DTYPE = "float16"
    BNB_4BIT_QUANT_TYPE = "nf4"
    USE_NESTED_QUANT = False

config = Config()
print("\n✓ Configuration loaded")

# ============================================================================
# DATASET PREPARATION
# ============================================================================

# Sample training data - In production, replace with your actual dataset
SAMPLE_TRAINING_DATA = [
    {
        "instruction": "Explain this FIR document in simple English",
        "input": """FIRST INFORMATION REPORT
Police Station: Connaught Place, Delhi
FIR No: 234/2024
Complainant: Rajesh Kumar, Age 45
Accused: Amit Sharma
Sections: IPC 420, 406
Details: Complainant invested Rs. 25 lakhs in real estate project based on false promises. Accused has not returned money or provided returns since August 2024.""",
        "output": """This is a case of cheating and criminal breach of trust. Rajesh Kumar (complainant) invested 25 lakh rupees in a real estate project, but Amit Sharma (accused) made false promises and hasn't returned the money.

Current Stage: FIR has been registered. Police investigation has begun.

What Happens Next:
1. Police will investigate and collect evidence
2. Accused may be arrested if sufficient proof is found
3. Chargesheet will be filed
4. Case will go to court trial

Available Options:
- Continue with police investigation and court case
- Attempt mediation if both parties agree
- Apply for legal aid if needed

Important: This typically takes 12-18 months for resolution."""
    },
    {
        "instruction": "इस FIR दस्तावेज़ को सरल हिंदी में समझाएं",
        "input": """प्रथम सूचना रिपोर्ट
थाना: कनॉट प्लेस, दिल्ली
FIR संख्या: 234/2024
शिकायतकर्ता: राजेश कुमार, आयु 45
आरोपी: अमित शर्मा
धाराएं: IPC 420, 406
विवरण: शिकायतकर्ता ने रियल एस्टेट परियोजना में 25 लाख रुपये का निवेश किया। आरोपी ने झूठे वादे किए और अगस्त 2024 से पैसे वापस नहीं किए।""",
        "output": """यह धोखाधड़ी और विश्वासघात का मामला है। राजेश कुमार (शिकायतकर्ता) ने रियल एस्टेट परियोजना में 25 लाख रुपये का निवेश किया, लेकिन अमित शर्मा (आरोपी) ने झूठे वादे किए और पैसे वापस नहीं किए।

वर्तमान स्थिति: FIR दर्ज की गई है। पुलिस जांच शुरू हो गई है।

आगे क्या होगा:
1. पुलिस जांच करेगी और सबूत इकट्ठा करेगी
2. यदि पर्याप्त सबूत मिलते हैं तो आरोपी को गिरफ्तार किया जा सकता है
3. आरोप पत्र दायर किया जाएगा
4. मामला न्यायालय में सुनवाई के लिए जाएगा

उपलब्ध विकल्प:
- पुलिस जांच और न्यायालय मामला जारी रखें
- यदि दोनों पक्ष सहमत हों तो मध्यस्थता का प्रयास करें
- यदि आवश्यक हो तो कानूनी सहायता के लिए आवेदन करें

महत्वपूर्ण: समाधान में आमतौर पर 12-18 महीने लगते हैं।"""
    },
    {
        "instruction": "Explain this court order in simple language",
        "input": """IN THE HIGH COURT OF DELHI
Civil Writ Petition No. 1234/2024
Petitioner: Sunita Devi vs Respondent: Municipal Corporation

ORDER
Date: 15th October 2024

The court has examined the petition. The petitioner has challenged the demolition notice issued by the respondent.

The court hereby directs:
1. The demolition is stayed for 30 days
2. Respondent to file reply within 15 days
3. Next hearing on 15th November 2024

If respondent fails to comply, the notice shall stand cancelled.""",
        "output": """This is a court order about a demolition notice dispute. Sunita Devi has challenged a demolition notice from Municipal Corporation.

Court's Decision:
- Demolition is stopped for 30 days
- Municipal Corporation must respond within 15 days
- Next hearing is on 15th November 2024

What This Means:
The demolition cannot happen for 30 days. The court will hear both sides on the next date.

What You Should Do:
1. Keep attending court hearings
2. Ensure your lawyer files all required documents
3. If the other party doesn't respond, the notice may be cancelled

Timeline: Matter will be heard again in 30 days. Final decision depends on both parties' arguments."""
    },
    {
        "instruction": "Explain this legal notice",
        "input": """LEGAL NOTICE
To: Mr. Anil Verma
From: Ms. Priya Sharma (through Advocate)
Date: 10th October 2024

Subject: Non-payment of loan amount

My client Ms. Priya Sharma lent you Rs. 5,00,000 on 1st January 2024 with agreement to repay by 1st July 2024.

Despite repeated requests, you have failed to repay. This is a formal demand to pay the full amount within 15 days.

If you fail to comply, my client will be forced to file a civil suit for recovery with interest and costs.""",
        "output": """This is a legal notice about unpaid loan. Priya Sharma (lender) claims Anil Verma (borrower) owes 5 lakh rupees that was due in July 2024.

Current Stage: Pre-litigation stage. This is a formal warning before filing a court case.

What's Being Asked:
Pay 5 lakh rupees within 15 days from the notice date.

What Happens Next:
1. If you pay within 15 days, matter is closed
2. If you don't pay, a court case may be filed
3. You can respond through your lawyer if you disagree

Your Options:
- Pay the amount if you agree
- Respond through lawyer if you disagree with the claim
- Try to negotiate a settlement
- Prepare for court case if no agreement

Important: Respond within 15 days. Ignoring this notice may lead to a court case.

Timeline: 15 days to respond. If case is filed, it may take 6-12 months."""
    }
]

# Create prompt formatting function
def format_instruction(sample):
    """Format training sample into instruction-following format"""
    return f"""### Instruction:
{sample['instruction']}

### Input:
{sample['input']}

### Response:
{sample['output']}"""

# Convert to dataset
def create_dataset(data):
    """Create HuggingFace dataset from list"""
    formatted_data = []
    for item in data:
        formatted_data.append({
            "text": format_instruction(item)
        })
    return Dataset.from_list(formatted_data)

# Load your actual training data here
# For demo, we use sample data
print("\n📚 Preparing dataset...")
train_dataset = create_dataset(SAMPLE_TRAINING_DATA)
print(f"✓ Training samples: {len(train_dataset)}")
print("\nSample formatted text:")
print(train_dataset[0]['text'][:500] + "...")

# ============================================================================
# MODEL SETUP
# ============================================================================

print("\n🤖 Loading base model...")

# Quantization config for memory efficiency
bnb_config = BitsAndBytesConfig(
    load_in_4bit=config.USE_4BIT,
    bnb_4bit_quant_type=config.BNB_4BIT_QUANT_TYPE,
    bnb_4bit_compute_dtype=getattr(torch, config.BNB_4BIT_COMPUTE_DTYPE),
    bnb_4bit_use_double_quant=config.USE_NESTED_QUANT,
)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    config.BASE_MODEL,
    trust_remote_code=True
)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"
print("✓ Tokenizer loaded")

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    config.BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)
print("✓ Base model loaded")

# Prepare model for training
model = prepare_model_for_kbit_training(model)
print("✓ Model prepared for k-bit training")

# ============================================================================
# LORA CONFIGURATION
# ============================================================================

print("\n🔧 Setting up LoRA...")

lora_config = LoraConfig(
    r=config.LORA_R,
    lora_alpha=config.LORA_ALPHA,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=config.LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
print("✓ LoRA configured")

# ============================================================================
# TRAINING CONFIGURATION
# ============================================================================

print("\n⚙️ Configuring training...")

training_arguments = TrainingArguments(
    output_dir=config.OUTPUT_DIR,
    num_train_epochs=config.NUM_EPOCHS,
    per_device_train_batch_size=config.BATCH_SIZE,
    gradient_accumulation_steps=config.GRADIENT_ACCUMULATION_STEPS,
    optim="paged_adamw_32bit",
    save_strategy="epoch",
    logging_steps=10,
    learning_rate=config.LEARNING_RATE,
    weight_decay=0.001,
    fp16=True,
    bf16=False,
    max_grad_norm=0.3,
    warmup_ratio=0.03,
    group_by_length=True,
    lr_scheduler_type="cosine",
    report_to="none"
)

# Setup trainer
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    tokenizer=tokenizer,
    args=training_arguments,
    peft_config=lora_config,
    dataset_text_field="text",
    max_seq_length=config.MAX_SEQ_LENGTH,
    packing=False,
)

print("✓ Trainer configured")

# ============================================================================
# TRAINING
# ============================================================================

print("\n🚀 Starting training...")
print("=" * 70)

# Train the model
trainer.train()

print("\n✓ Training completed!")

# ============================================================================
# SAVE MODEL
# ============================================================================

print("\n💾 Saving model...")

# Save the fine-tuned model
trainer.model.save_pretrained(f"{config.OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{config.OUTPUT_DIR}/final")

print(f"✓ Model saved to {config.OUTPUT_DIR}/final")

# ============================================================================
# TESTING
# ============================================================================

print("\n🧪 Testing model...")

# Load the fine-tuned model for inference
test_model = AutoModelForCausalLM.from_pretrained(
    config.BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto"
)

test_model = PeftModel.from_pretrained(test_model, f"{config.OUTPUT_DIR}/final")

# Create pipeline
pipe = pipeline(
    "text-generation",
    model=test_model,
    tokenizer=tokenizer,
    max_new_tokens=512,
    temperature=0.7,
    top_p=0.95,
    repetition_penalty=1.15
)

# Test prompt
test_prompt = """### Instruction:
Explain this FIR in simple English

### Input:
FIR No: 123/2024
Complainant: Ram Kumar
Accused: Shyam Lal
Sections: IPC 379 (Theft)
Details: Complainant's motorcycle was stolen from parking. CCTV footage shows accused taking the vehicle.

### Response:
"""

print("\nTest Input:")
print("-" * 70)
print(test_prompt)
print("-" * 70)

result = pipe(test_prompt)
print("\nModel Output:")
print("-" * 70)
print(result[0]['generated_text'].split("### Response:")[-1].strip())
print("-" * 70)

# ============================================================================
# EVALUATION METRICS
# ============================================================================

print("\n📊 Training Summary:")
print("=" * 70)
print(f"✓ Base Model: {config.BASE_MODEL}")
print(f"✓ Training Samples: {len(train_dataset)}")
print(f"✓ Epochs: {config.NUM_EPOCHS}")
print(f"✓ Batch Size: {config.BATCH_SIZE}")
print(f"✓ Learning Rate: {config.LEARNING_RATE}")
print(f"✓ LoRA Rank: {config.LORA_R}")
print(f"✓ Model Size: ~7B parameters")
print(f"✓ Trainable Parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
print("=" * 70)

print("\n✅ All done! Model is ready for deployment.")
print(f"\nTo use the model in your application:")
print(f"1. Download model from: {config.OUTPUT_DIR}/final")
print(f"2. Load using: PeftModel.from_pretrained(base_model, 'path/to/model')")
print(f"3. Deploy with FastAPI backend")

# ============================================================================
# INSTRUCTIONS FOR USING IN PRODUCTION
# ============================================================================

print("\n" + "=" * 70)
print("📖 PRODUCTION DEPLOYMENT GUIDE")
print("=" * 70)

deployment_code = """
# In your FastAPI backend (main.py):

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel
import torch

# Load model
base_model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.2",
    torch_dtype=torch.float16,
    device_map="auto"
)

model = PeftModel.from_pretrained(base_model, "path/to/nyayagpt-final")
tokenizer = AutoTokenizer.from_pretrained("path/to/nyayagpt-final")

# Create pipeline
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512
)

# Use in endpoint
def explain_document(text: str, language: str):
    prompt = f'''### Instruction:
Explain this legal document in simple {language}

### Input:
{text}

### Response:
'''
    result = generator(prompt)
    return result[0]['generated_text'].split("### Response:")[-1].strip()
"""

print(deployment_code)
print("=" * 70)
