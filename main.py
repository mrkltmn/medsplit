from pathlib import Path

from src.medsplit.read_files import read_files


def main() -> None:
    path = Path.cwd()

    read_files(path)


if __name__ == "__main__":
    main()
