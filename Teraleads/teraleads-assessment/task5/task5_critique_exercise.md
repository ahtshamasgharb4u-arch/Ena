# Task 5: Critique Exercise — Junior Engineer's Hallucination Answer

## The Junior's Answer

> _"I would use Chain-of-Thought prompting and increase the temperature so the model thinks harder. I would also use RAG which retrieves information from a vector database so the model has more context. To reduce hallucinations specifically, I would add 'Do not hallucinate' to the system prompt and increase the max_tokens so it does not get cut off. We should also fine-tune the model with LoRA on customer data which usually fixes hallucinations."_

---

## Markup

| Statement                                                                           | Verdict                      | Explanation                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Use Chain-of-Thought prompting"                                                    | ✅ **Partially right**       | CoT can improve reasoning for multi-step questions (e.g., "Do I need a referral for a root canal?"), but it does **not** reduce hallucinations by itself. In fact, CoT can _increase_ hallucination risk on factual questions because the model generates intermediate reasoning steps that may be wrong.                                                                                            |
| "Increase the temperature so the model thinks harder"                               | ❌ **Wrong**                 | Higher temperature increases randomness, making the model _more_ likely to hallucinate, not less. Lower temperature (0.0–0.3) is preferred for factual QA to reduce creativity and stick to retrieved context. The phrase "thinks harder" confuses temperature with reasoning effort.                                                                                                                |
| "Use RAG which retrieves information from a vector database"                        | ✅ **Right, but incomplete** | RAG is the correct approach. But the junior doesn't mention _how_ to use the retrieved context: grounding the LLM's answer in the retrieved chunks, citation, or what happens when retrieval returns nothing. RAG without grounding is just "more context" — the model can still ignore it.                                                                                                          |
| "Add 'Do not hallucinate' to the system prompt"                                     | ❌ **Wrong**                 | This is a placebo instruction. LLMs do not have an internal "hallucinate" flag that a negative command can toggle off. Research shows such instructions have negligible effect. The correct approach is to constrain the model with a grounded generation template: _"Answer only using the provided context. If the context does not contain the answer, say 'I don't know'."_                      |
| "Increase the max_tokens so it does not get cut off"                                | ❌ **Wrong / irrelevant**    | Truncation (being cut off) is not a significant cause of hallucinations. If the answer is cut off, the issue is that the model ran out of tokens mid-response, which is a separate problem from hallucination. Increasing `max_tokens` does not reduce hallucination — it may actually increase it by giving the model more room to generate unsupported text.                                       |
| "Fine-tune the model with LoRA on customer data which usually fixes hallucinations" | ⚠️ **Dangerously wrong**     | LoRA fine-tuning on customer data does **not** fix hallucinations. In fact, fine-tuning on a small, narrow dataset can _increase_ hallucination risk by overfitting the model to spurious patterns. Fine-tuning is for style/tone adaptation, not factual accuracy. For factual QA, RAG + prompt engineering is the correct approach. Fine-tuning should be a last resort, not a first-line defense. |

---

## What Is Missing

The junior's answer misses the most effective hallucination reduction techniques:

1. **Grounding instructions.** The single most effective technique: _"Answer ONLY using the provided context. If the context does not contain the answer, say 'I don't know'."_ This is not mentioned at all.

2. **Citation / source attribution.** Requiring the model to cite which chunk supports each claim (e.g., `[1]`, `[2]`) lets you verify faithfulness programmatically. Not mentioned.

3. **Confidence thresholding.** If the retriever's similarity score is below a threshold, refuse to answer rather than hallucinate. Not mentioned.

4. **Input guardrails.** Classify the query before retrieval. Out-of-scope questions (diagnosis, prognosis) should be deflected before they reach the LLM. Not mentioned.

5. **Output validation.** A post-generation check: does the answer contain claims not present in the retrieved chunks? This can be done with a second LLM call (LLM-as-judge) or a simple NLI model. Not mentioned.

6. **Evaluation.** How would you _measure_ hallucination rate? Without metrics, "reducing hallucinations" is a vague goal. Not mentioned.

---

## What I Would Say in a Code Review

> "Thanks for thinking about this. Let me walk through each point.
>
> **Chain-of-Thought** — good idea for multi-step reasoning, but it won't reduce hallucinations on factual questions. In fact, it can make them worse because the model generates intermediate steps that may be wrong. Reserve CoT for questions that actually need reasoning.
>
> **Temperature** — this is backwards. Higher temperature increases randomness, which increases hallucination risk. For factual QA, set temperature to 0.1 or lower. The model doesn't 'think harder' with higher temperature — it just becomes more creative, which is the opposite of what we want.
>
> **RAG** — this is the right direction, but you're missing the most important part: grounding. Just retrieving context isn't enough. The system prompt must say: 'Answer ONLY using the provided context. If the context doesn't contain the answer, say you don't know.' Without that, the model treats the retrieved chunks as optional reading.
>
> **'Do not hallucinate'** — this doesn't work. LLMs don't have a 'hallucinate' switch. Replace it with a grounded generation template and a refusal instruction.
>
> **Max tokens** — being cut off is a separate issue from hallucination. If the answer is truncated, the fix is either increasing max_tokens or shortening the response, not using it as a hallucination strategy.
>
> **LoRA fine-tuning** — this is the most concerning part. Fine-tuning on customer data does not fix hallucinations. It can actually make them worse by overfitting. Fine-tuning is for adapting style or tone, not for factual accuracy. For this use case, RAG + prompt engineering is the right approach. Let's not fine-tune unless we have a very specific reason and a way to measure that it doesn't degrade factual accuracy.
>
> **What's missing:** grounding instructions, citation, confidence thresholds, input guardrails, output validation, and an evaluation plan. Let's start with a grounded RAG prompt, add citation, and measure hallucination rate before and after. That will give us real data on whether we're actually reducing hallucinations."
