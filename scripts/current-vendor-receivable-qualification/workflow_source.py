"""Focused pre-push check of this qualifier's step keys, not a full Actions lint."""
import yaml

STEP_KEYS={'name','id','if','uses','run','with','env','working-directory','shell','timeout-minutes','continue-on-error'}


def checked(text):
    workflow=yaml.safe_load(text)
    for job_id,job in workflow['jobs'].items():
        for index,step in enumerate(job['steps'],1):
            unknown=set(step)-STEP_KEYS
            if unknown:raise ValueError('VENDOR_WORKFLOW_UNKNOWN_STEP_KEY:'+job_id+':'+str(index)+':'+','.join(sorted(unknown)))
            if ('run'in step)==('uses'in step):raise ValueError('VENDOR_WORKFLOW_EXACTLY_ONE_RUN_OR_USES_REQUIRED')
    return workflow
