---
language: python
license: apache-2.0
base_model: Qwen2.5-Coder-7B-Instruct
tags:
- code-generation
- lora
- research
---

# Reason-Code LoRA (Draft)

## Model Description
This is a LoRA-finetuned variant of Qwen2.5-Coder-7B-Instruct, trained on self-generated code repair traces.

## Training Data
- Internal synthetic repair trajectories
- Success / failure cases collected from sandbox execution

## Intended Use
Research only.  
Not intended for production deployment.

## Limitations
- Limited training data
- No extensive safety evaluation
- Not benchmarked against public leaderboards