"""Fetch exact accepted bytes before source admission; no database access."""
from hashlib import sha256
from pathlib import Path
import importlib.util,io,json,os,subprocess,zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('combined_fetch_evidence_gate',HERE/'evidence.py')
evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)


def fetch():
    config=json.loads((HERE/'PREREQUISITES.json').read_bytes());binding=evidence.gate(config)
    retained=json.loads((HERE.parent/'current-finance-consistency-followup-qualification/CONFIG.json').read_bytes())
    assert retained['retained84']==binding['retained84'],'COMBINED_RETAINED84_BINDING_CHANGED'
    directories=[]
    for key,variable in (('retained84','original_directory_variable'),('focused','focused_directory_variable')):
        proof=binding[key]
        raw=subprocess.check_output(['gh','api',
            'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
        assert len(raw)==proof['zip_bytes'] and sha256(raw).hexdigest()==proof['zip_sha256']
        directory=Path(os.environ['RUNNER_TEMP'])/('combined-consistency-'+key);directory.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw))as archive:
            assert archive.testzip()is None and len(archive.namelist())==len(set(archive.namelist()))
            for member,name,size,digest in (
                (proof['archive_member'],proof['name'],proof['bytes'],proof['sha256']),
                (proof['package_member'],proof['package_name'],proof['package_bytes'],proof['package_sha256'])):
                assert Path(name).name==name and name.endswith('.json')
                assert archive.namelist().count(member)==1
                data=archive.read(member);assert len(data)==size and sha256(data).hexdigest()==digest
                (directory/name).write_bytes(data)
        directories.append((config[variable],directory))
        if key=='retained84':directories.append((retained['original_directory_variable'],directory))
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:
        for variable,directory in directories:stream.write(variable+'='+str(directory)+'\n')
    print(json.dumps(dict(retained_head=binding['retained84']['head'],retained_whole_status='INCOMPLETE',
        focused_head=binding['focused']['head'],accepted_bytes_fetched=True,
        full_source_and_runtime_acceptance_requires_admission=True)))


if __name__=='__main__':fetch()
