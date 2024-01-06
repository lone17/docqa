import os

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from wandb.integration.openai.fine_tuning import WandbLogger

load_dotenv(find_dotenv(".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Upload files
train_file = "data/generative_agent/main-dense-long-instruction.jsonl"
train_file_obj = client.files.create(file=open(train_file, "rb"), purpose="fine-tune")
train_file_id = train_file_obj.id

val_file = "data/generative_agent/summary-dense+sparse-long-instruction.jsonl"
val_file_obj = client.files.create(file=open(val_file, "rb"), purpose="fine-tune")
val_file_id = val_file_obj.id

# Create finetune job
finetune_job_obj = client.fine_tuning.jobs.create(
    training_file=train_file_id,
    validation_file=val_file_id,
    model=os.getenv("OPENAI_MODEL"),
    suffix="gen-agent-v2",
)

# Synchronize with Wandb
WandbLogger.sync(
    fine_tune_job_id=finetune_job_obj.id,
    project="aitomatic-openai-finetune",
)
