"""Explicit current475 source/Original study; future runtime stays NULL-closed."""
import argparse
import json
import source_check


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--offline', action='store_true')
    choice.add_argument('--current-originals', action='store_true')
    choice.add_argument('--runtime', action='store_true')
    args = parser.parse_args(argv)
    if args.offline:
        print(json.dumps(source_check.check()))
    elif args.current_originals:
        import current_originals
        print(json.dumps(current_originals.admitted()))
    else:
        from probe import runtime
        print(json.dumps(runtime().admitted()))


if __name__ == '__main__':
    main()
