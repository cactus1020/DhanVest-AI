"""Pass server-only database configuration to Vercel via stdin, never CLI args."""
from pathlib import Path
import shutil
import subprocess
import json
import tempfile
import sys

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
values = dotenv_values(root / '.env')
cli = shutil.which('vercel.cmd') or shutil.which('vercel')
if not cli:
    raise SystemExit('Installed Vercel CLI not found.')
project = json.loads((root / 'frontend/.vercel/project.json').read_text())
variables = []
for name in (['CRON_SECRET'] if '--cron-only' in sys.argv else ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']):
    value = values.get(name)
    if not value:
        raise SystemExit('Missing server configuration: ' + name)
    variables.append({'key': name, 'value': value, 'type': 'sensitive', 'target': ['preview', 'production']})
# The authenticated CLI handles token refresh and team scope. A private,
# temporary JSON body avoids both command-line secrets and branch prompts.
for variable in variables:
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     delete=True, delete_on_close=False) as body:
        json.dump(variable, body)
        body.close()
        result = subprocess.run([cli, 'api', '/v10/projects/' + project['projectId'] + '/env?upsert=true',
                                 '-X', 'POST', '--input', body.name, '--silent'],
                                cwd=root / 'frontend', text=True, capture_output=True)
    if result.returncode:
        error = f'CLI exit status: {result.returncode}\n' + result.stderr + result.stdout
        for secret in values.values():
            if secret: error = error.replace(secret, '[REDACTED]')
        raise SystemExit(error)
    print('Configured', variable['key'], 'as sensitive for Preview and Production.')
