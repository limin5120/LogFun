import time
import random
import string
import sys
from LogFun import traced, basicConfig

# Configure Remote mode to interact with Manager
basicConfig(mode='remote', logtype='compress', app_name='balancer_test_app')

# --- 1. Atomic Functions (Designed for frequent external calls) ---


@traced
def process_item_low_entropy(idx):
    """
    Scenario A: Low Entropy Task.
    Uses a fixed template with a predictable variable (modulo).
    Expected Behavior:
      - Z-Score: Muted due to high frequency.
      - Weighted Entropy: Muted due to low information content.
    """
    # Modulo 5 ensures the variable repeats often, keeping entropy low
    process_item_low_entropy._log("Checking system status: module=%s status=OK", idx % 5)


@traced
def process_item_high_entropy():
    """
    Scenario B: High Entropy Task.
    Uses a fixed template but with highly random variables.
    Expected Behavior:
      - Z-Score: Muted (if only checking frequency).
      - Weighted Entropy: Kept ACTIVE (high information value), despite high frequency.
    """
    # Generate a random string to simulate unique transaction IDs
    rand_token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    process_item_high_entropy._log("Processing distinct transaction. Token: %s", rand_token)


# --- 2. Test Runner ---


def run_load_test(func, iterations, interval=0.01, desc=""):
    print(f"\n[Test] {desc}")
    print(f"-> Running {iterations} iterations with {interval}s interval...")

    start_time = time.time()

    for i in range(iterations):
        if func == process_item_low_entropy:
            func(i)
        else:
            func()

        # Small sleep allows:
        # 1. Network I/O thread to send logs
        # 2. Agent to receive 'Mute' commands from Manager
        time.sleep(interval)

        if (i + 1) % 50 == 0:
            sys.stdout.write(f"\rProgress: {i + 1}/{iterations}")
            sys.stdout.flush()

    print(f"\n<- Finished in {time.time() - start_time:.2f}s")


# --- 3. Main Execution Flow ---

if __name__ == "__main__":
    print("=== Balancer Optimization Test ===")
    print("Prerequisite: Ensure 'python -m LogFun.manager.server' is running.\n")

    # --- Phase 1: Z-Score Test ---
    print("--- Phase 1: Z-Score Strategy (Frequency Only) ---")
    print("Please go to Manager Dashboard -> Active Strategy -> ⚙️ Settings")
    print("Set to: [Z-Score] with Window=60, Threshold=2.0")
    # input("Press Enter when ready...")

    run_load_test(process_item_low_entropy, iterations=300, interval=0.005, desc="Simulating High Frequency Spam (Expect AUTO-MUTE)")

    # --- Phase 2: Weighted Entropy Test ---
    print("\n--- Phase 2: Weighted Entropy Strategy (Smart Filter) ---")
    print("Please go to Manager Dashboard -> Active Strategy -> ⚙️ Settings")
    print("Set to: [Weighted Entropy] with Window=60, Threshold=2.0, Min Entropy=2.0")
    print("Note: This strategy should mute repetitive logs but allow unique ones.")
    # input("Press Enter when ready...")

    # 2.1 Low Entropy -> Should be Muted
    run_load_test(process_item_low_entropy, iterations=300, interval=0.005, desc="Part A: Low Entropy Spam (Expect AUTO-MUTE)")

    print("\nWaiting 5s for sliding window to clear...")
    time.sleep(5)

    # 2.2 High Entropy -> Should remain Active
    run_load_test(process_item_high_entropy, iterations=300, interval=0.005, desc="Part B: High Entropy Burst (Expect ACTIVE)")

    print("\n=== Test Complete ===")
    print("Check the Manager Dashboard to verify the 'Status' column changes.")
