# STATUS: REVIEWED by Manoj on 15-10-2026
 Reviewer notes: all three families are made up. Check each story sounds like a tired parent typing on a phone,
# contains no disease names, and that the ages are plausible. Arjun uses case neg08 from review/negatives.yaml.
<!--
The three example families judges will click through. All made up.
The build picks the dev-split case whose signs best match each story (+ the doctor letter for Kabir) and
uses that case to answer the follow-up questions in replay. `make review-check` validates this file.
-->

## Kabir
- age_months: 30
- expected_path: story → 2 home rounds → see a doctor → doctor letter → referral ready → "6 months later" check
- match_criteria: multi-system (nervous system + at least one other), ≥ 8 recorded signs, presenting signs a parent can see
- story: |
  Kabir is two and a half and I am worried because he is so different from his cousin who is the same age. He was very floppy as a baby, like a rag doll, and he took forever to hold his head up. He only started sitting at about 14 months and he still cannot walk without holding my hands. He has maybe five words. He feeds slowly and chokes on lumpy food, so he is still on purees, and he gets a lot of chest infections. His right eye turns inwards when he is tired. The health visitor said he is small for his age and his head is on the small side. Our doctor heard a murmur in his heart when he was a baby but nobody followed it up. Everyone says boys are slow, but my gut says something is not right.

## Arjun
- age_months: 30
- negatives_case: neg08
- expected_path: story → 1–2 rounds → no escalation ("mention at your next routine visit")
- match_criteria: none (uses a case from review/negatives.yaml with expected: no_escalation)
- story: |
  Arjun is two and a half. For a few months last year he walked on his tiptoes everywhere, in the garden, in the house, even on the beach, and it made me nervous. My mother-in-law said I was making a fuss, but I read online that it can mean something serious so I wanted to ask. Over the last couple of months he has mostly stopped and now walks flat on his feet most of the time. He runs, jumps off the bottom step and climbs on the sofa like any other toddler. He talks in little sentences, eats well and sleeps through. I suppose I just want someone to tell me whether I should still be worried about the tiptoe walking or whether I can relax.

## Maya
- age_months: 20
- expected_path: story → emergency rule fires → urgent screen, nothing else
- match_criteria: none (story must trigger rule seizure_long_or_repeated)
- story: |
  Maya is 20 months old. About ten minutes ago she went stiff and then her arms and legs started jerking and she was not responding to us at all, her eyes were rolled back. It lasted about ten minutes and it is still not completely over, she is very sleepy and floppy now. She has had a cold and a temperature since yesterday. I have never seen anything like this and my husband is shouting for me to do something. I am writing this on my phone because I did not know what else to do.