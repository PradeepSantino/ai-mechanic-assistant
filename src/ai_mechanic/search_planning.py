"""Build bounded mechanical searches from structured question interpretation."""
import json
import re

PLANNING_PROMPT = '''Interpret a service-manual question. Return JSON only:
{"vehicle_context":"vehicle details stated by the user", "tasks":[{"component":"mechanical component", "operation":"requested action or specification"}]}.
Correct spelling. Resolve short follow-up references from the supplied history.
Put make, model, year, registration, engine and drivetrain information ONLY in
vehicle_context. Do not infer missing engine codes, specifications or answers.
Each component and operation must be short search terms, without vehicle details.
Use at most three tasks for distinct mechanical questions. For greetings use [].
Example question: for a 2012 Toyota RAV4 what is the alternatior mouting bolt torque?
Example JSON: {"vehicle_context":"2012 Toyota RAV4", "tasks":[{"component":"alternator", "operation":"mounting bolt torque"}]}'''


def parse_search_plan(raw, fallback):
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip())
    plan = json.loads(raw)
    if not isinstance(plan, dict) or not isinstance(plan.get('tasks'), list):
        raise ValueError('Invalid search plan')
    queries = []
    for task in plan['tasks'][:3]:
        if not isinstance(task, dict):
            continue
        component, operation = task.get('component'), task.get('operation')
        if not isinstance(component, str) or not isinstance(operation, str):
            continue
        query = ' '.join((component + ' ' + operation).split())
        if not query or len(query) > 200:
            continue
        # Toyota uses generator and headlining for these common workshop terms.
        query = re.sub(r'\balternator\b', 'generator', query, flags=re.I)
        query = re.sub(r'\broof (?:lining|liner)\b', 'headlining', query, flags=re.I)
        if query not in queries:
            queries.append(query)
    return queries or [fallback]
