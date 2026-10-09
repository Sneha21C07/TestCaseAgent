import importlib
import sys

modules = [
    'scripts.requirements_parser',
    'scripts.requirements_embeddings',
    'scripts.requirements_index',
    'scripts.flow_templates',
    'scripts.flow_builder',
    'scripts.scenario_generator',
    'scripts.generate_test_cases',
]

ok = True
for m in modules:
    try:
        importlib.import_module(m)
        print(m + ' OK')
    except Exception as e:
        ok = False
        print(m + ' ERR', e)

if not ok:
    sys.exit(1)
