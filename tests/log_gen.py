import random
import sys
import time

PII_TEMPLATES = [
    "User {i} logged in with email test{i}@example.com",
    "Connection from 192.168.1.{i}",
    "Payment processed for user{i}@domain.org",
]


def generate_logs(count=10, delay=0.0):
    for i in range(count):
        template = random.choice(PII_TEMPLATES)
        log = template.format(i=i)
        print(log)
        sys.stdout.flush()
        if delay > 0:
            time.sleep(delay)


if __name__ == "__main__":
    generate_logs(count=50)
