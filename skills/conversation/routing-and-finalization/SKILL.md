---
name: routing-and-finalization
description: Route one conversational turn and finalize one bounded user-facing response.
metadata:
  author: rps
  version: "2.0"
---
Route conversational turns without doing domain planning yourself.

Method:
1. classify the turn into the correct bounded mode
2. send it to exactly one specialist path
3. finalize the reply without changing the specialist decision

Hard rules:
- do not do hidden domain work in the router
- do not merge several operations into one turn unless already confirmed by the specialist result
