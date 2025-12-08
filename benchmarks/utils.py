import json
import random
from typing import Any, Dict, Generator

# Sample PII data for generation
EMAILS = [
    "test@example.com",
    "user.name@domain.co.uk",
    "security@company.org",
    "fake.email@service.net",
]
PHONES = ["555-0199", "(555) 123-4567", "123-456-7890", "+1-555-555-5555"]
NAMES = ["John Doe", "Jane Smith", "Alice Wonderland", "Bob Builder"]
SENTENCES = [
    "This is a sample sentence with some data.",
    "Please contact me at {} for more info.",
    "My phone number is {}.",
    "Confidential report for {}.",
    "Here is some random filler text to bulk up the size.",
]


def generate_large_text(size_mb: float = 1.0) -> str:
    """
    Generates a large string of approximately `size_mb` megabytes containing PII.
    """
    target_bytes = int(size_mb * 1024 * 1024)
    buffer = []
    current_bytes = 0

    while current_bytes < target_bytes:
        template = random.choice(SENTENCES)
        # Randomly insert PII or just plain text
        if "{}" in template:
            if "phone" in template:
                filler = random.choice(PHONES)
            elif "contact" in template:
                filler = random.choice(EMAILS)
            else:
                filler = random.choice(NAMES)
            text = template.format(filler)
        else:
            text = template

        buffer.append(text)
        current_bytes += len(text) + 1  # +1 for newline or space

    return "\n".join(buffer)


def generate_chunk_stream(
    text: str, chunk_size: int = 1024
) -> Generator[str, None, None]:
    """
    Yields chunks of `text` of size `chunk_size`.
    """
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


def generate_flat_json(size_mb: float = 1.0) -> str:
    """
    Generates a large JSON string (list of flat objects) of approximately `size_mb`.
    """
    target_bytes = int(size_mb * 1024 * 1024)
    data = []
    current_bytes = 0

    # Estimate size of one record to batches
    while current_bytes < target_bytes:
        record = {
            "id": random.randint(1000, 9999),
            "name": random.choice(NAMES),
            "email": random.choice(EMAILS),
            "phone": random.choice(PHONES),
            "notes": (
                random.choice(SENTENCES).format(random.choice(EMAILS))
                if "{}" in random.choice(SENTENCES)
                else "No notes."
            ),
        }
        data.append(record)
        # Rough estimation of JSON size overhead
        current_bytes += 100  # Approx bytes per record

    return json.dumps(data)


def generate_nested_json(depth: int = 5, size_mb: float = 1.0) -> Dict[str, Any]:
    """
    Generates a deeply nested JSON object (dict).
    Returns the object, not string, as traverse_and_redact expects an object.
    Size approximation is loose here.
    """
    # For nested JSON, we'll create a recursive structure.
    # To hit size_mb, we can make a list of these nested structures.

    def create_nested_node(current_depth):
        if current_depth == 0:
            return {"leaf_info": random.choice(NAMES), "contact": random.choice(EMAILS)}

        return {
            "level": current_depth,
            "manager": random.choice(NAMES),
            "sub_node_a": create_nested_node(current_depth - 1),
            "sub_node_b": create_nested_node(current_depth - 1),
            "details": [random.choice(EMAILS) for _ in range(5)],
        }

    # To get volume, we'll create a top-level list containing many such trees
    # A single tree of depth 5 is decent size, but we need many to hit 1MB.

    target_bytes = int(size_mb * 1024 * 1024)
    large_structure = {"data": []}
    current_estimated_bytes = 0

    while current_estimated_bytes < target_bytes:
        node = create_nested_node(depth)
        large_structure["data"].append(node)
        current_estimated_bytes += len(json.dumps(node))

    return large_structure
