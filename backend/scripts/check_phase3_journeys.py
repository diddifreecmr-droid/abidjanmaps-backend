from scripts.check_phase3_map_traces import run_checks


if __name__ == "__main__":
    import json

    print(json.dumps(run_checks(), ensure_ascii=True))
