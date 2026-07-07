"""
Echo Registry Analyzer (ERA)
run.py
Version: 0.4.3
"""

from engines.merge_engine import MergeEngine
from engines.patient_engine import PatientEngine
from engines.disease_engine import DiseaseEngine
from engines.statistics_engine import StatisticsEngine


def main():
    MergeEngine().run()
    PatientEngine().run()
    DiseaseEngine().run()
    StatisticsEngine().run()


if __name__ == "__main__":
    main()
