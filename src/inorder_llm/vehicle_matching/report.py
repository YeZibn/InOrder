"""Run the offline vehicle matcher comparison as a module."""

from .dataset import EVALUATION_SAMPLES
from .evaluation import evaluate, render_report


def main() -> None:
    reports = evaluate(EVALUATION_SAMPLES)
    print(render_report(reports))
    for report in reports:
        print(f"\n[{report.strategy}]")
        for result in report.results:
            print(f"{result.text}\t{result.candidate_code or '-'}\t{result.score:.1f}\t{'accept' if result.accepted else 'abstain'}\t{result.reason}")


if __name__ == "__main__":
    main()
