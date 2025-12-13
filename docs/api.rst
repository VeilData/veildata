.. _api:

API Reference
=============

This section documents the public API of ``veildata``.

Main Interface
--------------

.. automodule:: veildata
   :members:
   :undoc-members:
   :show-inheritance:

Redactors
---------

The core of VeilData is the Redactor interface.

.. autoclass:: veildata.redactors.regex.RegexRedactor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: veildata.redactors.ner_spacy.SpacyNERRedactor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: veildata.redactors.ner_bert.BERTNERRedactor
   :members:
   :undoc-members:
   :show-inheritance:

Composition & Pipeline
----------------------

.. autoclass:: veildata.transforms.Compose
   :members:
   :undoc-members:

.. autoclass:: veildata.pipeline.Pipeline
   :members:
   :undoc-members:

Reversibility
-------------

.. autoclass:: veildata.revealers.TokenStore
   :members:
   :undoc-members:

Configuration
-------------

.. automodule:: veildata.core.config
   :members:
   :undoc-members:

Engine
------

.. automodule:: veildata.engine
   :members:
   :undoc-members:

Streaming
---------

.. automodule:: veildata.streaming_buffer
   :members:
   :undoc-members:
