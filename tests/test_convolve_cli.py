import pathlib
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from pineko.cli._base import command


def test_convolve_cli_read_only_and_multi_operator(monkeypatch, tmp_path):
    """Test that convolve CLI opens operators in read mode and supports multiple operators."""
    runner = CliRunner()

    grid_file = tmp_path / "test_grid.pineappl"
    grid_file.touch()

    op1_file = tmp_path / "op1.tar"
    op1_file.touch()
    op2_file = tmp_path / "op2.tar"
    op2_file.touch()

    fk_out = tmp_path / "output.fk"

    mock_grid = MagicMock()
    monkeypatch.setattr("pineappl.grid.Grid.read", lambda path: mock_grid)
    monkeypatch.setattr("pineko.theory_card.load", lambda tid: {"PTO": 1})

    mock_op1 = MagicMock()
    mock_op2 = MagicMock()
    mock_op1.__enter__.return_value = mock_op1
    mock_op2.__enter__.return_value = mock_op2

    read_calls = []

    def mock_read(path):
        read_calls.append(pathlib.Path(path))
        return mock_op1 if "op1" in str(path) else mock_op2

    def mock_edit(path):
        pytest.fail("EKO.edit should NOT be called; read-only EKO.read must be used")

    monkeypatch.setattr("eko.EKO.read", mock_read)
    monkeypatch.setattr("eko.EKO.edit", mock_edit)

    evolve_called_with = []

    def mock_evolve_grid(grid, operators, fktable, *args, **kwargs):
        evolve_called_with.append((grid, operators, fktable))
        return grid, None, None

    monkeypatch.setattr("pineko.evolve.evolve_grid", mock_evolve_grid)

    result = runner.invoke(
        command,
        [
            "convolve",
            str(fk_out),
            str(grid_file),
            "53",
            "1",
            "0",
            str(op1_file),
            str(op2_file),
        ],
    )

    assert result.exit_code == 0
    # Both operators opened with EKO.read
    assert read_calls == [op1_file, op2_file]
    # Both operators entered and passed to evolve_grid
    assert len(evolve_called_with) == 1
    assert evolve_called_with[0][1] == [mock_op1, mock_op2]
    # Both operators exited/closed cleanly
    mock_op1.__exit__.assert_called_once()
    mock_op2.__exit__.assert_called_once()
