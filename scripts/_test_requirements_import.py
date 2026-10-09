import importlib.util
import json
p = r"u:/Users/rj612959/workspace/UIUX_Siebel - J8 - Copy (2)/UIUX_Siebel - J8 - Copy/scripts/requirements_to_tests.py"
spec = importlib.util.spec_from_file_location('reqmod', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('HAS_PARSE', hasattr(mod, 'parse_requirements'))
print('HAS_GENERATE', hasattr(mod, 'generate_tests'))
reqs = [{'id':'REQ-0001','heading':'Login Journey','text':'Users must login. Validate required fields and error messages.'}]
outs = mod.generate_tests(reqs)
print('OUT_COUNT', len(outs))
print(json.dumps(outs, indent=2)[:1000])
