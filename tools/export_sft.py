import json
import os

def export_sft(output_path="sft_data.jsonl", max_items=None):
    out = []
    # 优先使用成功样本
    for fname in ["logs/success_cases.jsonl", "logs/fail_cases.jsonl"]:
        if not os.path.exists(fname):
            continue
        with open(fname, "r", encoding="utf-8") as f:
            for i,line in enumerate(f):
                if max_items and len(out) >= max_items:
                    break
                try:
                    obj = json.loads(line)
                except:
                    continue
                if fname.endswith("success_cases.jsonl"):
                    prompt = obj.get("prompt","")
                    response = obj.get("corrected","")
                else:
                    prompt = obj.get("prompt","")
                    # 失败样本：把 candidate+stderr 当作 response，鼓励模型学习修复
                    response = obj.get("candidate","") + "\n# STDERR:\n" + obj.get("stderr","")
                out.append({"prompt": prompt, "response": response})
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in out:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Exported {len(out)} SFT examples to {output_path}")

if __name__ == "__main__":
    export_sft()