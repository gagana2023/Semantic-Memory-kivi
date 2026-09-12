import argparse
import json
import sys
from pathlib import Path
from .config import Settings
from .evaluation import create_run, run, run_complete
from .storage import connect
from .review import import_corpus, reset_database, verify_model_lock, write_model_lock

def main():
    parser = argparse.ArgumentParser(prog="python -m kivi")
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--case-set", default="development")
    evaluate.add_argument("--wait", action="store_true")
    evaluate.add_argument("--corpus", default="fixtures/development-500.json")
    evaluate.add_argument("--questions", default="EVAL_QUESTIONS.json")
    evaluate.add_argument("--ground-truth", default="GROUND_TRUTH.json")
    evaluate.add_argument("--output-dir", default=".")
    imported = sub.add_parser("import-corpus")
    imported.add_argument("path")
    imported.add_argument("--timeout-seconds", type=int, default=300)
    sub.add_parser("reset")
    sub.add_parser("write-model-lock")
    sub.add_parser("verify-model-lock")
    sub.add_parser("inspect-memory")
    args = parser.parse_args()
    if args.command == "evaluate":
        settings = Settings(); result=run_complete(settings,args.corpus,args.questions,args.ground_truth,args.output_dir)
        passed=result["summary"]["passed"]; total=result["summary"]["total"]
        output=Path(args.output_dir).resolve()
        complete=passed == total
        print(json.dumps({
            "status":"✅ Evaluation complete" if complete else "⚠️ Evaluation complete: some checks failed",
            "passed":passed,
            "total":total,
            "files_created":[str(output / "results.json"),str(output / "summary.md")],
        },ensure_ascii=False,sort_keys=True))
        if not complete: sys.exit(1)
        return
    settings = Settings()
    if args.command == "import-corpus":
        print(json.dumps(import_corpus(settings, args.path, args.timeout_seconds), sort_keys=True))
    elif args.command == "reset":
        print(json.dumps(reset_database(settings), sort_keys=True))
    elif args.command == "write-model-lock":
        print(json.dumps(write_model_lock(settings), sort_keys=True))
    elif args.command == "verify-model-lock":
        print(json.dumps(verify_model_lock(settings), sort_keys=True))
    elif args.command == "inspect-memory":
        db=connect(settings)
        try:
            rows=[]
            for memory in db.execute("SELECT * FROM memories ORDER BY created_at,id"):
                item=dict(memory); item['type']=item['kind']; item['supersession_status']=item['status']; item['provenance']=[x['transcript_id'] for x in db.execute("SELECT transcript_id FROM memory_evidence WHERE memory_id=? ORDER BY transcript_id",(memory['id'],))]
                rows.append(item)
            print(json.dumps({'memories':rows},indent=2,ensure_ascii=False,sort_keys=True))
        finally: db.close()
if __name__ == "__main__": main()
