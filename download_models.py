"""
This is used in Dockerfile to prevent downloading models during run time.
"""
from angle_emb import AnglE
from marker.models import load_all_models

load_all_models()
AnglE.from_pretrained("WhereIsAI/UAE-Large-V1", pooling_strategy="cls")
