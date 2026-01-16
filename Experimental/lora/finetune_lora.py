import json
import os
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model, TaskType

def main():
    model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct" 
    output_dir = "lora-reason-coder-v3"
    
    print(f"载入基座模型: {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, 
        torch_dtype=torch.float16, # M1 MPS 支持 FP16
        device_map="auto"          # 自动分配到 MPS
    )

    # LoRA 配置适配 Llama 架构
    print("应用 LoRA 配置...")
    lora_config = LoraConfig(
        r=16,               # 增加秩，提升拟合能力
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        # Qwen/Llama 的核心层，必须覆盖，否则效果很差
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"] 
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 3.数据处理 (使用 Chat Template)
    print("加载并格式化数据...")
    sft_path = "logs/success_cases.jsonl" # 确保这里有数据，或者用 augmented_sft_data.jsonl
    data = []
    
    # 简单的 fallback 数据，防止文件为空报错
    if not os.path.exists(sft_path) or os.path.getsize(sft_path) == 0:
        print("⚠️ 警告：没有找到训练数据，使用内置Dummy数据")
        raw_data = [{"original": "def add(a,b): return a-b", "corrected": "def add(a,b): return a+b"}]
    else:
        with open(sft_path, "r", encoding="utf-8") as f:
             # 兼容你的日志格式
            raw_data = []
            for line in f:
                try: 
                    j = json.loads(line)
                    if j.get("type") == "success": raw_data.append(j)
                except: pass

    # 构建 ChatML 格式，这符合 "Instruct" 模型的训练方式
    for j in raw_data:
        messages = [
            {"role": "system", "content": "你是一个Python代码修复专家。请修复输入的代码错误。"},
            {"role": "user", "content": f"{j['original']}"},
            {"role": "assistant", "content": j['corrected']}
        ]
        # 使用 tokenizer 自动应用模板 (Qwen自带模板)
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        data.append({"text": text})

    dataset = Dataset.from_list(data)

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=512,
            padding="max_length",
        )

    tokenized = dataset.map(tokenize, batched=True)
    # Mask掉 User 部分的 Loss (高级技巧，可选，这里简化全算Loss)
    tokenized = tokenized.map(lambda x: {"labels": x["input_ids"]}, batched=True)

    # 4训练参数优化
    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,     # 数据少时多跑几轮
        per_device_train_batch_size=2, # M1 上 2 或 1
        gradient_accumulation_steps=4, # 显存不够就用梯度累积
        learning_rate=2e-4,     # LoRA 通常用大一点的 LR
        fp16=True,              # 开启混合精度
        logging_steps=1,
        save_strategy="epoch",
        optim="adamw_torch"     # M1 兼容性较好的优化器
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )

    print("开始训练...")
    trainer.train()
    
    print(f"保存模型到 {output_dir}")
    trainer.save_model(output_dir)
    # 同时也保存 tokenizer，方便推理时加载
    tokenizer.save_pretrained(output_dir)

if __name__ == "__main__":
    main()