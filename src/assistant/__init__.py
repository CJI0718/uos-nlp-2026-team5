"""Schedule assistant: finds tech/game events, verifies them with the Task A
verification server and gate, and keeps them in an in-app schedule.

The LLM never writes to the schedule. It only calls the verification tools;
every schedule change goes through the deterministic policy (`policy.py`) and
the Task A gate (`task_a.missions.validate_mission_gate`).
"""
