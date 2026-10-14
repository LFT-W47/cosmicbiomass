"""The package announces its deprecation where its users will see it."""

import subprocess
import sys

import cosmicbiomass


def test_import_warns_with_default_filters() -> None:
    # A fresh interpreter with Python's default warning filters, as in a user's
    # script: the warning must not depend on pytest enabling it.
    completed = subprocess.run(
        [sys.executable, "-c", "import cosmicbiomass"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "FutureWarning" in completed.stderr
    assert "deprecated" in completed.stderr
    assert "neptoon" in completed.stderr


def test_message_names_the_successor_and_the_unit_change() -> None:
    message = cosmicbiomass.DEPRECATION_MESSAGE

    assert "neptoon[geo]" in message
    assert "kg/m2" in message and "Mg/ha" in message
    assert cosmicbiomass.__version__ == "0.2.4"
