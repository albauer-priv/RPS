# Load Estimation Trace Flags

Every planning layer should be able to explain:
- which IF reference source was used
- whether segment parsing or fallback estimation was used
- whether uncertainty or fallback assumptions were active

Trace expectations:
- confidence claims must reflect input quality
- fallback use should be visible to reviewers and auditors
