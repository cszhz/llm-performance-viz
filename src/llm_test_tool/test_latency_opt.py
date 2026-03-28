#!/usr/bin/env python3
"""
Test inference latency for gpt-oss-20b model on Bedrock
"""

import time
import boto3
import json
import pandas as pd

# Read test data from xlsx
df = pd.read_excel('/home/ubuntu/llm_web/gpt-oss/score_samples.xlsx')
df = df.head(100)  # First 100 rows

print("=" * 60)
print("Latency Test for gpt-oss-20b on Bedrock (100 samples)")
print("=" * 60)

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2'
)

model_id = 'openai.gpt-oss-20b-1:0'
#model_id = 'openai.gpt-oss-safeguard-20b'

##Reasoning: minimal
# System message from build_system_message() in prompt.jinja
SYSTEM_MESSAGE = """You are a multilingual text safety filter for game chat. Detect insults, vulgar, sexual content and evasion variants.
Reasoning: low

Keep analysis under 20 words then output final answer.

# Valid channels: final. Channel must be included for every message."""

latencies = []
errors = 0

for idx, row in df.iterrows():
    prompt = row['prompt']

    body = json.dumps({
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.7,
    })

    start_time = time.time()

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body,
            contentType='application/json',
            accept='application/json'
        )

        end_time = time.time()
        latency = end_time - start_time
        latencies.append(latency)

        # Parse response to get token usage and output
        response_body = json.loads(response['body'].read())
        usage = response_body.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)

        # Get model output
        output = ""
        if 'choices' in response_body and response_body['choices']:
            output = response_body['choices'][0].get('message', {}).get('content', '')

        print(f"[{idx+1:2d}/100] Latency: {latency*1000:7.1f} ms | Prompt tokens: {prompt_tokens:4d} | Output tokens: {completion_tokens}")
        print(f"         Output: {output}")

    except Exception as e:
        end_time = time.time()
        latency = end_time - start_time
        errors += 1
        print(f"[{idx+1:2d}/100] ERROR after {latency*1000:.1f} ms: {type(e).__name__}")

print("\n" + "=" * 60)
print("Statistics")
print("=" * 60)

if latencies:
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    print(f"Total requests:    {len(latencies) + errors}")
    print(f"Successful:        {len(latencies)}")
    print(f"Errors:            {errors}")
    print(f"\nAverage latency:   {avg_latency*1000:.1f} ms ({avg_latency:.3f} s)")
    print(f"Min latency:       {min_latency*1000:.1f} ms")
    print(f"Max latency:       {max_latency*1000:.1f} ms")
    print(f"Total time:        {sum(latencies):.1f} s")
else:
    print("No successful requests")

print("=" * 60)
