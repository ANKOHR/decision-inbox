# Lessons for KOML

The domain requires a distinction between a decision, routine execution, and routine execution that lacks a next action. Missing next actions should not inflate the decision queue. The engine exposes that third condition as a separate readiness count while keeping two queues.

Validated on planted synthetic evidence: explicit decision flags, alternatives, and missing information can be separated deterministically with exact reconciliation. Changing a decision record changes the computed figures, and changing the expectations file alone does not change output. Real-world usefulness and accuracy remain unmeasured.

An implementation assumption broke during adversarial testing: output escaping could be adjusted without affecting user text. Two tests failed when forbidden punctuation was accidentally left literal. The fix restores Unicode escapes in rendered output while JSON parsing recovers the original input. Both round-trip and surface restrictions are tested.

Operating rule: every classification must show its explicit trigger and source record. Never turn a supplied effort estimate into measured savings, or synthetic rule agreement into human-use accuracy.
