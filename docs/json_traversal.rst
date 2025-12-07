
Structured JSON Traversal
=========================

VeilData supports recursive redaction of nested JSON structures (dictionaries and lists) while preserving the original structure and non-string types.

This functionality is provided by the ``veildata.traversal`` module.

Usage
-----

.. code-block:: python

   from veildata.utils.traversal import traverse_and_redact
   from veildata.redactors.regex import RegexRedactor

   # 1. Setup your redactor (or use a pipeline)
   redactor = RegexRedactor(patterns=["SECRET"])

   # 2. Define your complex data
   data = {
       "user": {
           "name": "John Doe",
           "bio": "I have a SECRET code.",
           "age": 42
       },
       "history": ["SECRET event", "Public event"]
   }

   # 3. Apply redaction
   # The redactor function must accept a string and return a string.
   # Here we check if the redactor is callable directly or if we need .redact()
   # RegexRedactor is callable in some versions, or use .redact
   redacted_data = traverse_and_redact(data, redactor.redact)

   print(redacted_data)
   # Output:
   # {
   #     "user": {
   #         "name": "John Doe",
   #         "bio": "I have a [REDACTED] code.",
   #         "age": 42
   #     },
   #     "history": ["[REDACTED] event", "Public event"]
   # }

API Reference
-------------

.. autofunction:: veildata.utils.traversal.traverse_and_redact
