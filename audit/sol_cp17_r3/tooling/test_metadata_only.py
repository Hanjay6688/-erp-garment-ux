"""Synthetic metadata checks only; no SQL, HTTP, business cases or CodeQL scan."""
import ast
import copy
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import codeql_metadata_gate as cg
import identity_metadata as im

REPO = Path(__file__).resolve().parents[3]
WORKFLOW_SHA = "d850ca7aeebdc3dfec15f2cc3190297e334a3273"


def candidate(path):
    return dict(path=path,head=im.CANDIDATE,tree=im.CANDIDATE_TREE,product_trees=copy.deepcopy(im.PRODUCT_TREES),
        absent_product_paths=[],tracked_product_diff="",lock_sha256="0"*64)


def historical():
    trees=copy.deepcopy(im.PRODUCT_TREES);trees.pop("scripts/cp7-src")
    return dict(path="auditor",head=im.HISTORICAL_UI,tree=im.HISTORICAL_UI_TREE,product_trees=trees,
        absent_product_paths=["scripts/cp7-src"],tracked_product_diff="",lock_sha256="0"*64)


class IdentityChecks(unittest.TestCase):
    def test_public_git_candidate_constants_match_actual_object(self):
        def git(*args):
            return subprocess.check_output(["git",*args],cwd=REPO,text=True).strip()
        self.assertEqual(git("rev-parse",im.CANDIDATE+"^{tree}"),im.CANDIDATE_TREE)
        self.assertEqual({p:git("rev-parse",im.CANDIDATE+":"+p)for p in im.PRODUCT_TREES},im.PRODUCT_TREES)
        self.assertEqual(git("rev-parse",im.HISTORICAL_UI+"^{tree}"),im.HISTORICAL_UI_TREE)

    def test_current_install_requires_two_exact_candidate_checkouts(self):
        out=im.validate_t3_records({"auditor":candidate("auditor"),"chain":candidate("chain")},"install",WORKFLOW_SHA)
        self.assertEqual(out["workflow_sha"],WORKFLOW_SHA)
        self.assertTrue(all(r["candidate_exact"]for r in out["checkouts"]))

    def test_pinned_historical_ui_can_record_missing_cp7_path(self):
        out=im.validate_t3_records({"auditor":historical(),"chain":candidate("chain")},"browser",WORKFLOW_SHA)
        self.assertFalse(out["checkouts"][0]["candidate_exact"])
        self.assertEqual(out["checkouts"][0]["absent_product_paths"],["scripts/cp7-src"])
        self.assertTrue(out["checkouts"][1]["candidate_exact"])

    def test_wrong_candidate_head_refused(self):
        r=candidate("chain");r["head"]=WORKFLOW_SHA
        with self.assertRaisesRegex(ValueError,"HEAD_MISMATCH"):im.validate_record(r,"candidate")

    def test_wrong_candidate_tree_refused(self):
        r=candidate("chain");r["tree"]="f"*40
        with self.assertRaisesRegex(ValueError,"TREE_MISMATCH"):im.validate_record(r,"candidate")

    def test_missing_candidate_path_refused(self):
        r=candidate("chain");r["product_trees"].pop("scripts/cp7-src");r["absent_product_paths"]=["scripts/cp7-src"]
        with self.assertRaises(ValueError):im.validate_record(r,"candidate")

    def test_changed_candidate_product_tree_refused(self):
        r=candidate("chain");r["product_trees"]["src"]="e"*40
        with self.assertRaisesRegex(ValueError,"PRODUCT_PATH_MISMATCH"):im.validate_record(r,"candidate")

    def test_dirty_product_worktree_refused(self):
        r=candidate("chain");r["tracked_product_diff"]="src/example.tsx"
        with self.assertRaisesRegex(ValueError,"WORKTREE_CHANGED"):im.validate_record(r,"candidate")

    def test_unpinned_historical_head_refused(self):
        r=historical();r["head"]="f"*40
        with self.assertRaisesRegex(ValueError,"HEAD_MISMATCH"):im.validate_record(r,"historical_ui")

    def test_historical_missing_path_must_be_explicit(self):
        r=historical();r["absent_product_paths"]=[]
        with self.assertRaisesRegex(ValueError,"PATH_NOT_EXPLICIT"):im.validate_record(r,"historical_ui")

    def test_no_candidate_chain_refused(self):
        with self.assertRaises(ValueError):im.validate_t3_records({"auditor":historical(),"chain":historical()},"browser",WORKFLOW_SHA)


class CodeqlMetadataChecks(unittest.TestCase):
    def test_product_and_workflow_sha_remain_separate(self):
        row=cg.bind_identity(im.CANDIDATE,im.CANDIDATE_TREE,WORKFLOW_SHA)
        self.assertEqual(row["head"],im.CANDIDATE)
        self.assertEqual(row["workflow_sha"],WORKFLOW_SHA)
        self.assertNotEqual(row["head"],row["workflow_sha"])

    def test_workflow_sha_cannot_masquerade_as_product(self):
        with self.assertRaisesRegex(ValueError,"PRODUCT_HEAD_MISMATCH"):cg.bind_identity(WORKFLOW_SHA,im.CANDIDATE_TREE,WORKFLOW_SHA)

    def test_wrong_tree_refused(self):
        with self.assertRaisesRegex(ValueError,"PRODUCT_TREE_MISMATCH"):cg.bind_identity(im.CANDIDATE,"f"*40,WORKFLOW_SHA)

    def test_workflow_sha_is_required(self):
        with self.assertRaisesRegex(ValueError,"WORKFLOW_SHA_INVALID"):cg.bind_identity(im.CANDIDATE,im.CANDIDATE_TREE,"")

    def test_existing_sarif_loop_and_result_predicate_unchanged(self):
        original=ast.parse((REPO/"scripts/cp6_codeql_artifact_gate.py").read_text())
        proposed=ast.parse(Path(cg.__file__).read_text())
        main=next(n for n in proposed.body if isinstance(n,ast.FunctionDef)and n.name=="main")
        old_loop=next(n for n in original.body if isinstance(n,ast.For))
        new_loop=next(n for n in main.body if isinstance(n,ast.For))
        self.assertEqual(ast.dump(old_loop),ast.dump(new_loop))
        def status(body):
            result=next(n.value for n in body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="result"for t in n.targets))
            return next(v for k,v in zip(result.keys,result.values)if isinstance(k,ast.Constant)and k.value=="status")
        self.assertEqual(ast.dump(status(original.body)),ast.dump(status(main.body)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
