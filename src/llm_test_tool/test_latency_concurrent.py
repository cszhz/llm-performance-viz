#!/usr/bin/env python3
"""
Test inference latency for gpt-oss-20b with QPS control
"""

import time
import boto3
import json
import pandas as pd
import queue
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Read test data
df = pd.read_excel('/home/ubuntu/llm_web/gpt-oss/score_samples.xlsx')
prompts = df['prompt'].tolist()

# Config
model_id = 'openai.gpt-oss-20b-1:0'
force_same_data = False
force_no_thinking = False

# System message from build_system_message() in prompt.jinja
SYSTEM_MESSAGE = """You are a multilingual text safety filter for game chat. Detect insults, vulgar, sexual content and evasion variants.
Reasoning: low

Keep analysis under 20 words then output final answer.

# Valid channels: final. Channel must be included for every message."""

# Thread-local storage for boto3 clients
thread_local = threading.local()

def get_client():
    if not hasattr(thread_local, 'client'):
        thread_local.client = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'
        )
    return thread_local.client


def worker(task_id, params, result_queue):
    """Single request worker"""
    client = get_client()
    prompt = params['prompt']

    body = json.dumps({
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.7,
    })

    start_time = time.perf_counter()
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType='application/json',
            accept='application/json'
        )
        latency = time.perf_counter() - start_time

        response_body = json.loads(response['body'].read())
        usage = response_body.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)

        output = ""
        if 'choices' in response_body and response_body['choices']:
            output = response_body['choices'][0].get('message', {}).get('content', '')

        result_queue.put({
            'task_id': task_id,
            'success': True,
            'latency': latency,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'output': output,
        })

    except Exception as e:
        latency = time.perf_counter() - start_time
        result_queue.put({
            'task_id': task_id,
            'success': False,
            'latency': latency,
            'error': str(e),
        })


def test_loop(n_per_second: int, run_seconds: int, prompts, max_workers: int = None):
    """
    n_per_second:  目标 QPS（每秒提交多少个请求）
    run_seconds:   压测持续时间（秒）
    prompts:       prompt 列表
    max_workers:   线程池并发数（在飞请求上限）
    """

    result_queue = queue.Queue()

    # 默认并发数：按 QPS 的一半给一个保守值
    if max_workers is None:
        max_workers = min(320, max(64, n_per_second))

    total_tasks = n_per_second * run_seconds
    pbar = tqdm(total=total_tasks, desc="Submitting", unit="task")

    # 控制在飞请求数，防止无限排队
    inflight = threading.Semaphore(max_workers)

    start = time.perf_counter()
    deadline = start + run_seconds
    task_id = 0

    def _wrapped_worker(task_id, params):
        try:
            worker(task_id, params, result_queue)
        except Exception as e:
            print(e)
        finally:
            inflight.release()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while task_id < total_tasks:
            now = time.perf_counter()

            # 到达整体超时，停止提交
            if now >= deadline:
                break

            # 计算该 task 理论上的发送时间
            target_time = start + task_id / n_per_second

            # 如果下一个请求已经超出压测窗口，直接退出
            if target_time >= deadline:
                break

            # 没到时间就 sleep，保证 QPS 稳定
            if now < target_time:
                time.sleep(min(target_time - now, deadline - now))
                continue

            # 背压：限制在飞请求数量，避免队列堆积
            remaining = deadline - now
            if remaining <= 0:
                break

            acquired = inflight.acquire(timeout=remaining)
            if not acquired:
                break

            if force_same_data:
                prompt = prompts[0]
            else:
                prompt = prompts[random.randrange(len(prompts))]

            if force_no_thinking:
                prompt += '\n\n /no_think'
            params = {"prompt": prompt}

            executor.submit(_wrapped_worker, task_id, params)

            task_id += 1
            pbar.update(1)

    pbar.close()
    return result_queue


def print_results(result_queue, total_time):
    """Print statistics from result queue"""
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    success_results = [r for r in results if r['success']]
    error_results = [r for r in results if not r['success']]

    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)

    # Print each result
    for r in sorted(results, key=lambda x: x['task_id']):
        if r['success']:
            print(f"[{r['task_id']:3d}] Latency: {r['latency']*1000:7.1f} ms | "
                  f"Tokens: {r['prompt_tokens']:4d}/{r['completion_tokens']:3d}")
            print(f"       Output: {r['output']}")
        else:
            print(f"[{r['task_id']:3d}] ERROR: {r['error'][:50]}")

    print("\n" + "=" * 70)
    print("Statistics")
    print("=" * 70)

    if success_results:
        latencies = [r['latency'] for r in success_results]
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # P50, P90, P99
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.5)]
        p90 = sorted_latencies[int(len(sorted_latencies) * 0.9)]
        p99 = sorted_latencies[min(int(len(sorted_latencies) * 0.99), len(sorted_latencies) - 1)]

        print(f"Total requests:        {len(results)}")
        print(f"Successful:            {len(success_results)}")
        print(f"Errors:                {len(error_results)}")
        print(f"\nLatency (ms):")
        print(f"  Avg:                 {avg_latency*1000:.1f}")
        print(f"  Min:                 {min_latency*1000:.1f}")
        print(f"  Max:                 {max_latency*1000:.1f}")
        print(f"  P50:                 {p50*1000:.1f}")
        print(f"  P90:                 {p90*1000:.1f}")
        print(f"  P99:                 {p99*1000:.1f}")
        print(f"\nTotal wall time:       {total_time:.1f} s")
        print(f"Actual throughput:     {len(success_results)/total_time:.2f} req/s")
    else:
        print("No successful requests")

    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='QPS-controlled latency test')
    parser.add_argument('--qps', type=int, default=10, help='Target QPS')
    parser.add_argument('--duration', type=int, default=10, help='Test duration in seconds')
    parser.add_argument('--workers', type=int, default=None, help='Max concurrent workers')
    parser.add_argument('--same-data', action='store_true', help='Use same prompt for all requests')
    parser.add_argument('--no-thinking', action='store_true', default=True, help='Add /no_think suffix (default: True)')
    args = parser.parse_args()

    force_same_data = args.same_data
    force_no_thinking = args.no_thinking

    print("=" * 70)
    print(f"QPS Test: target={args.qps} QPS, duration={args.duration}s")
    print(f"Expected total requests: {args.qps * args.duration}")
    print("=" * 70)

    start_time = time.perf_counter()
    result_queue = test_loop(
        n_per_second=args.qps,
        run_seconds=args.duration,
        prompts=prompts,
        max_workers=args.workers
    )
    total_time = time.perf_counter() - start_time

    print_results(result_queue, total_time)
