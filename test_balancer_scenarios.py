import time
import random
import string
from LogFun import traced, basicConfig

# Remote mode is required to communicate with the Manager's Balancer
basicConfig(mode='remote', logtype='compress', app_name='balancer_test_app')


def get_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters, k=length))


# Scenario A: High-frequency, Low-entropy (Repetitive Spam)
# Expected: Should be muted by Weighted Entropy strategy due to low information content.
@traced
def spam_bot_low_entropy():
    for i in range(500):
        # Repetitive template and predictable variable i
        spam_bot_low_entropy._log("Connection failed, retrying attempt %s...", i)
        time.sleep(0.001)


# Scenario B: High-frequency, High-entropy (Valid Burst)
# Expected: Should be retained even if frequency is high, as the content is unique.
@traced
def valid_burst_high_entropy():
    for i in range(500):
        # Unique/Random variables increase entropy
        uuid = get_random_string(16)
        valid_burst_high_entropy._log("Processing distinct transaction ID: %s", uuid)
        time.sleep(0.001)


# Scenario C: Normal Baseline
@traced
def normal_heartbeat():
    for i in range(5):
        normal_heartbeat._log("System heartbeat tick %s", i)
        time.sleep(0.5)


if __name__ == "__main__":
    print("=== Balancer Scenario Testing ===")
    print("Ensure LogFun Manager is running with 'weighted_entropy' enabled.")

    print("\n[1] Sending normal heartbeats...")
    normal_heartbeat()

    print("\n[2] Simulating Low Entropy Spam...")
    # This should trigger the Mute action in Manager
    spam_bot_low_entropy()

    print("Waiting for Balancer analysis...")
    time.sleep(5)

    print("\n[3] Simulating High Entropy Burst...")
    # This should stay active despite high frequency
    valid_burst_high_entropy()

    print("\nTest completed. Check the Manager Dashboard for 'Auto-Muted' labels.")
