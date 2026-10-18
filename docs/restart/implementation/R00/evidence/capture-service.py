"""Diagnostic observation only: return the original subprocess result unchanged."""
import json
import sys
from pathlib import Path
lab=Path(sys.argv[1]); output=Path(sys.argv[2]);sys.path.insert(0,str(lab))
from scripts import integration_companion_service_context as module
original=module.run_command

def observe(*args, **kwargs):
    result=original(*args, **kwargs)
    if kwargs.get('capture_output') and kwargs.get('input') == '':
        output.write_text(json.dumps({'argv':result.args,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
    return result

module.run_command=observe
raise SystemExit(module.main())
