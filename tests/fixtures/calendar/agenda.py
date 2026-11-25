import json
import sys


def entries(day, rows):
    return [row["id"] for row in rows if row["start"][:10] == day and not row["cancelled"]]


if __name__ == "__main__":
    with open(sys.argv[2], encoding="utf-8") as src:
        print(json.dumps(entries(sys.argv[1], json.load(src))))
