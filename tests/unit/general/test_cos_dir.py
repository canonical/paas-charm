# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""COS merged directory behavior unit tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ops import testing

from paas_charm.charm import PaasCharm


def test_build_cos_dir_skips_merge_if_persistent_dir_exists(
    generic_context: testing.Context,
    generic_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    arrange: given a persisted merged COS directory.
    act: when build_cos_dir is called.
    assert: merge is skipped and the persisted directory is returned.
    """
    merged_dir = tmp_path / "explicit" / "cos_merged"
    merged_dir.mkdir(parents=True)

    merge_mock = MagicMock()
    monkeypatch.setattr("paas_charm.charm.merge_cos_directories", merge_mock)

    with generic_context(generic_context.on.start(), testing.State(**generic_state)) as manager:
        charm: PaasCharm = manager.charm
        monkeypatch.setattr(charm, "get_cos_merged_dir", lambda: merged_dir)
        merge_mock.reset_mock()
        assert charm.build_cos_dir() == merged_dir
    merge_mock.assert_not_called()


def test_build_cos_dir_merges_once_when_persistent_dir_missing(
    generic_context: testing.Context,
    generic_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    arrange: given no persisted merged COS directory.
    act: when build_cos_dir is called.
    assert: default and custom COS directories are merged into the persistent directory.
    """
    default_dir = tmp_path / "default"
    custom_dir = tmp_path / "custom"
    merged_dir = tmp_path / "fresh" / "cos_merged"

    default_dir.mkdir()
    custom_dir.mkdir()

    merge_mock = MagicMock()
    monkeypatch.setattr("paas_charm.charm.merge_cos_directories", merge_mock)

    with generic_context(generic_context.on.start(), testing.State(**generic_state)) as manager:
        charm: PaasCharm = manager.charm
        monkeypatch.setattr(charm, "get_cos_default_dir", lambda: default_dir)
        monkeypatch.setattr(charm, "get_cos_custom_dir", lambda: custom_dir)
        monkeypatch.setattr(charm, "get_cos_merged_dir", lambda: merged_dir)
        merge_mock.reset_mock()
        assert charm.build_cos_dir() == merged_dir
    merge_mock.assert_called_once_with(default_dir, custom_dir, merged_dir)
