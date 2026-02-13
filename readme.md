Based on the analysis of your codebase and the requirements, here is the professional English version of the `README.md` file.

---

# LogFun: An Efficient Function-Level Log Management Framework for Systems Implemented with Python

> **LogFun, a function-level logging framework that achieves efficient logging and runtime control. It enables efficient log compression and extraction of log templates and variables, as well as automatically identifies high-frequency and redundant logs natively.**

---

## 📝 Introduction

LogFun is a high-performance function-level log management framework designed specifically for Python systems. By decoupling log templates from variables, it achieves extreme log compression rates (typically < 10% of the original size).

Unlike traditional text-based logging libraries, LogFun introduces the concept of a **Manager (Control Plane)**. This allows developers to dynamically enable or disable specific functions or individual log statements at runtime without restarting the application. Furthermore, it natively integrates algorithms to automatically identify and intercept abnormal high-frequency "spam" logs, protecting production environments from I/O and network exhaustion.

---

## ✨ Key Features

* **⚡ Extreme Performance & Compression**: Utilizes a `Template ID` + `Variables` transmission protocol, significantly reducing network bandwidth and disk usage. The client employs asynchronous queues and batch sending mechanisms to minimize the impact on business performance.
* **🛡️ Fine-Grained Runtime Control**: Supports dynamic toggling of any function or specific log statement via a Web UI, with immediate effect on the Agent side.
* **🤖 Intelligent Traffic Shaping (Balancer)**:
* **Z-Score**: Automatically detects frequency anomalies based on statistical analysis.
* **Weighted Entropy**: Distinguishes between "high-frequency meaningless spam" and "high-frequency critical business logs" by analyzing information entropy.


* **🔍 Full-Link Tracing & Restoration**: Even in compressed mode, the framework perfectly restores plaintext logs with timestamps and log levels via the matching Decoder.
* **📊 Visual Management Platform**: Provides real-time QPS monitoring, log statistics, online queries, streaming downloads, and offline decompression capabilities.

---

## 🏗 Architecture & Structure

### Core Components

```text
LogFun/
├── LogFun/
│   ├── core/                  # [Client] Log Collection Core (Agent)
│   │   ├── agent.py           # Buffering, batch processing, local/remote dispatch
│   │   ├── coreFunction.py    # @traced decorator, compression protocol encapsulation
│   │   ├── registry.py        # Unified registry for Function ID & Template ID mapping
│   │   ├── net.py             # TCP Client with async send queue & heartbeat
│   │   └── logger.py          # Logger interface implementation
│   └── manager/               # [Server] Log Control Platform (Manager)
│       ├── server.py          # TCP Server handling log reception & heartbeats
│       ├── web.py             # Flask Web Server providing API & Dashboard
│       ├── balancer.py        # Traffic shaping algorithms (Z-Score / Entropy)
│       ├── decoder.py         # Core engine for log decompression & searching
│       ├── storage.py         # Persistence for configs & logs
│       └── templates/         # Frontend HTML resources
├── demo_LogFun.py             # Basic functionality demo
├── test_performance.py        # Performance benchmark script
├── test_balancer_scenarios.py # Auto-interception algorithm test cases
└── requirements.txt           # Dependency list

```

---

## 📦 Prerequisites & Installation

### Environment

* Python 3.8+
* Flask (Required only for the Manager side)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/your-repo/LogFun.git
cd LogFun

```


2. **Install dependencies**:
```bash
pip install -r requirements.txt

```


*(Note: The core client library depends only on the Python standard library; Flask is used solely for the Manager's Web UI)*

---

## 🚀 Quick Start

### Client Integration

Import `LogFun` into your Python project. Here is a minimal example:

```python
import time
from LogFun import traced, basicConfig

# Initialize Configuration
# mode: 'dev' (console), 'file' (local compressed file), 'remote' (send to Manager)
basicConfig(mode='remote', logtype='compress', app_name='my_app')

@traced
def process_data(user_id, value):
    # Use the _log interface for structured logging
    # Using %s placeholders is recommended for best compression
    process_data._log("Processing user %s with value %s", (user_id, value))
    
    if value > 90:
        process_data._log("High value detected: %s", value)

if __name__ == "__main__":
    while True:
        process_data(1001, 95)
        time.sleep(1)

```

### Server Deployment (Manager)

Start the Manager service on another machine or terminal to receive logs and serve the console:

```bash
# Run from the project root directory
python -m LogFun.manager.server

```

* **TCP Listening Port**: Default `9999` (For receiving logs)
* **Web Console**: Default `http://localhost:9998`

---

## 🖥 Web Dashboard Guide

Access `http://localhost:9998` to open the management interface.

### 1. Dashboard & Control

* **Global Monitoring**: View real-time QPS, total log count, uptime, and the currently active interception strategy.
* **Configuration Tree**:
* Displays all registered functions and their internal log templates.
* **Toggle Control**: Click `Disable` to mute a specific function or log statement in real-time (effective immediately on the Agent).
* **Status Indicators**:
* <span style="color:#00b894; background:#e6fffa; padding:2px 6px; border-radius:4px;">ON</span>: Normal collection.
* <span style="color:#ff7675; background:#ffeaea; padding:2px 6px; border-radius:4px;">OFF</span>: Manually disabled.
* <span style="color:#6c5ce7; background:#dfe6e9; padding:2px 6px; border-radius:4px;">AUTO</span>: Automatically intercepted by the Balancer.





### 2. Log Explorer

* **Online Search**: Supports full-text search by `Function Name`, `Template` (log content), or `Variable` (variable values).
* **Offline Decode**:
* Upload local `.log` (compressed logs) and `.json` (configuration files).
* The system will decode and display plaintext logs with timestamps and levels directly in the browser.



### 3. Traffic Shaping Strategies (Balancer)

Click the ⚙️ settings icon on the "Active Strategy" card in the Dashboard to dynamically switch algorithms:

* **Z-Score**: Detects anomalies based solely on frequency bursts (suitable for catching infinite loops).
* **Weighted Entropy**: Combines frequency and information entropy (suitable for distinguishing between "repetitive errors" and "high-frequency transactional logs").

---

## 🧪 Benchmarks & Tests

The repository includes three core test scripts covering functionality, performance, and algorithm verification.

### 1. Basic Function Test

Run `demo_LogFun.py` to verify basic logging, file writing, and network transmission capabilities.

```bash
python demo_LogFun.py

```

### 2. Performance Benchmark

Run `test_performance.py` to compare execution time and storage usage against `logging` (native) and `Loguru`.

```bash
python test_performance.py

```

*Expected Result*: LogFun's storage usage should be approximately 1/10th of traditional logging methods.

### 3. Auto-Interception Algorithm Test

Run `test_balancer_scenarios.py` to simulate "Low Entropy Spam" and "High Entropy Burst" scenarios, verifying that the Manager correctly identifies and intercepts only the former.

```bash
# 1. Ensure the Manager is running
python -m LogFun.manager.server

# 2. Run the test script
python test_balancer_scenarios.py

```

*Observation*: On the Web Console, the status of the `spam_bot_low_entropy` function should change to **AUTO** (Auto-Muted), while `valid_burst_high_entropy` remains **ON**.

---