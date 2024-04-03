import argparse
from mat.mat import Mat


def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        type=str,
        choices=['status', 'migrate', 'rollback'],
        help="Action to execute"
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Scriba configurations file. Default: ./migrations.yml"
    )

    parser.add_argument(
        "--steps",
        "-s",
        type=int,
        help="Number of scripts to run"
    )

    return parser.parse_args()


def main():
    args = _parse_args()
    file_path = "migrations.yml"

    if args.config:
        file_path = args.config

    mat = Mat(file_path)

    if args.action == "status":
        mat.status()

    if args.action == "migrate":
        mat.migrate(steps=args.steps)

    if args.action == "rollback":
        mat.rollback(steps=args.steps)


if __name__ == "__main__":
    main()
