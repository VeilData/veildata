import sys
import time


def mock_agent():
    """
    Simulates a Datadog Agent accepting logs via pipe.
    It reads stdin line by line and verifies the format.
    """
    print("Mock Agent: Listening on STDIN...", file=sys.stderr)

    received_count = 0
    valid_count = 0

    start_time = time.time()

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            received_count += 1

            # Simple validation: Did we receive redaction?
            if "[EMAIL]" in line or "[IP]" in line:
                valid_count += 1
                # print(f"Agent Received (Valid): {line}", file=sys.stderr)
            else:
                print(f"Agent Received (Unredacted?): {line}", file=sys.stderr)

    except KeyboardInterrupt:
        pass

    duration = time.time() - start_time

    print("\n--- Mock Agent Report ---", file=sys.stderr)
    print(f"Duration: {duration:.2f}s", file=sys.stderr)
    print(f"Total Logs Received: {received_count}", file=sys.stderr)
    print(f"Redacted Logs Verified: {valid_count}", file=sys.stderr)

    if received_count > 0 and received_count == valid_count:
        print("STATUS: SUCCESS (All logs received and redacted)", file=sys.stderr)
        sys.exit(0)
    else:
        print("STATUS: FAILURE (Missing logs or redaction)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    mock_agent()
