"""
Echo Registry Analyzer (ERA)
run.py
Version: 0.3.0
"""

from engines.merge_engine import MergeEngine
from engines.patient_engine import PatientEngine


def main():
    MergeEngine().run()
    PatientEngine().run()


if __name__ == "__main__":
    main()
