"""Prepare two local proposed workflows and a reviewable diff. Does not publish."""
import copy
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PROPOSED=HERE/"proposed_workflows"
ORIGINAL_WORKFLOW_SHA="d850ca7aeebdc3dfec15f2cc3190297e334a3273"


def sha(text):return hashlib.sha256(text.encode()).hexdigest()


def main():
    PROPOSED.mkdir(exist_ok=True)
    changes=[];patches=[]
    specifications=[
        ("audit-sol-r3-cp6-t3-release-package.yml","Sol record exact candidate and product trees","identity_metadata.py","SOL_IDENTITY_METADATA"),
        ("audit-sol-r3-cp6-candidate-codeql.yml","Verify analysis and bind SARIF to candidate","codeql_metadata_gate.py","SOL_CODEQL_METADATA"),
    ]
    for filename,name,helper,marker in specifications:
        path=REPO/".github/workflows"/filename
        before=subprocess.check_output(["git","show",ORIGINAL_WORKFLOW_SHA+":.github/workflows/"+filename],cwd=REPO,text=True)
        original=yaml.safe_load(before);after=copy.deepcopy(original)
        if helper=="identity_metadata.py":
            after["name"]="AUDIT/Sol/T3 browser metadata qualification"
            after["run-name"]="AUDIT/cp17-r3/Sol/b53b5acd/t3-browser-metadata-q1/1"
            include=after["jobs"]["phase"]["strategy"]["matrix"]["include"]
            after["jobs"]["phase"]["strategy"]["matrix"]["include"]=[r for r in include if r["key"]=="browser"]
            assert len(after["jobs"]["phase"]["strategy"]["matrix"]["include"])==1
        else:
            after["name"]="AUDIT/Sol/CodeQL metadata qualification"
            after["run-name"]="AUDIT/cp17-r3/Sol/b53b5acd/codeql-metadata-q1/1"
        matches=[]
        renamed_artifacts=[]
        for jobkey,job in after["jobs"].items():
            for index,step in enumerate(job["steps"]):
                if step.get("uses","").startswith("actions/upload-artifact"):
                    artifact=step.get("with",{}).get("name")
                    if artifact:
                        step["with"]["name"]=artifact.replace("cp17-r3-Sol-b53b5acd-","cp17-r3-Sol-b53b5acd-metadata-q1-",1)
                        assert step["with"]["name"]!=artifact
                        renamed_artifacts.append((jobkey,index,artifact,step["with"]["name"]))
                if step.get("name")==name:
                    code=(HERE/helper).read_text()
                    step["run"]="python3 - <<'"+marker+"'\n"+code+"\n"+marker
                    if helper=="identity_metadata.py":step["env"]={"SOL_T3_PHASE":"${{ matrix.key }}"}
                    matches.append((jobkey,index))
        assert len(matches)==1
        # Prove the parsed workflow changed only the named metadata step fields.
        restored=copy.deepcopy(after)
        for jobkey,index in matches:restored["jobs"][jobkey]["steps"][index]=copy.deepcopy(original["jobs"][jobkey]["steps"][index])
        for jobkey,index,oldname,newname in renamed_artifacts:restored["jobs"][jobkey]["steps"][index]["with"]["name"]=oldname
        restored["name"]=original["name"]
        restored["run-name"]=original["run-name"]
        if helper=="identity_metadata.py":restored["jobs"]["phase"]["strategy"]=copy.deepcopy(original["jobs"]["phase"]["strategy"])
        assert restored==original
        # Check that the exact tested helper is the embedded metadata program.
        jobkey,index=matches[0];run=after["jobs"][jobkey]["steps"][index]["run"]
        assert run.split("\n",1)[1].rsplit("\n",1)[0].rstrip("\n")==code.rstrip("\n")
        proposed=yaml.safe_dump(after,sort_keys=False,width=120000)
        (PROPOSED/filename).write_text(proposed)
        reparsed=yaml.safe_load(proposed);assert reparsed==after
        patches.extend(difflib.unified_diff(before.splitlines(True),proposed.splitlines(True),fromfile="a/.github/workflows/"+filename,tofile="b/.github/workflows/"+filename))
        changes.append(dict(path=".github/workflows/"+filename,original_sha256=sha(before),proposed_sha256=sha(proposed),
            helper=helper,helper_sha256=sha(code),changed_step=name,
            workflow_name={"before":original["name"],"after":after["name"]},
            run_name={"before":original["run-name"],"after":after["run-name"]},
            artifact_names=[dict(before=a,after=b)for _,_,a,b in renamed_artifacts],
            matrix_before=original["jobs"][jobkey]["strategy"]["matrix"],matrix_after=after["jobs"][jobkey]["strategy"]["matrix"],
            all_other_parsed_workflow_fields_unchanged=True))
    patchtext="".join(patches);(HERE/"METADATA_ONLY.patch").write_text(patchtext)
    manifest=dict(scope="LOCAL_METADATA_COLLECTION_REPAIR_ONLY_NOT_PUBLISHED",candidate_sha="b53b5acdf260b03ebac3474e9ae837fcef6f6eb1",
        candidate_tree="32f54240a60e01ab8b1ffad7267d285a669be520",original_workflow_sha=ORIGINAL_WORKFLOW_SHA,
        patch_sha256=sha(patchtext),changes=changes,
        declared_harness_changes=["T3 identity hook distinguishes the exact historical UI checkout from the exact candidate chain checkout.",
            "T3 matrix restricted to browser; completed install/capture retain their original evidence.",
            "CodeQL product HEAD/tree are pinned independently from workflow SHA; original SARIF query/loop/pass predicate unchanged.",
            "Workflow/run/artifact names mark metadata-q1; initial failures remain untouched."],
        initial_evidence={"t3":{"run_id":39146762759,"retained_install_job":117732074327,"retained_capture_job":117732074500,"precase_browser_failure_job":117732074565},
            "codeql":{"run_id":39146762479,"jobs":[117732073334,117732073546,117732073565,117732073589]}},
        prospective_jobs={"t3_browser":1,"codeql_languages":4,"t3_install_repeated":False,"t3_capture_repeated":False},
        application_changes=False,sql_changes=False,business_case_changes=False,codeql_query_changes=False,
        permissions_changes=False,checkout_ref_changes=False,workflow_triggered=False,published=False,
        verification="Synthetic metadata identity positive/negative checks; public Git object constants; SARIF loop/status AST equivalence. No scan, SQL, HTTP or business probe executed.")
    (HERE/"PATCH_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(dict(patch_sha256=manifest["patch_sha256"],workflow_paths=[c["path"]for c in changes],
        prospective_jobs=manifest["prospective_jobs"],published=False)))


if __name__=="__main__":main()
