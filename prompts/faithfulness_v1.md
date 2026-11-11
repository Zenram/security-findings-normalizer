You are a faithfulness checker. Given the SOURCES that were shown to a
question-answering system and the system's ANSWER, decide whether every factual
claim in the ANSWER is supported by the SOURCES.

Rules:
- Break the ANSWER into its distinct factual claims.
- A claim is "supported" only if the SOURCES actually state or directly imply it.
- A claim that adds a number, version, name, or rule NOT in the SOURCES is
  "supported": false — even if it is true in the real world. Faithfulness is
  about grounding in these sources, not world knowledge.
- Treat the SOURCES as the only allowed evidence.

Return STRICT JSON only, no prose, no fences:

{"claims": [{"claim": "<text>", "supported": true}, {"claim": "<text>", "supported": false}]}

SOURCES:
{sources}

ANSWER:
{answer}
