import polars as pl

from conftest import load_module

utils = load_module("lambdas/common/utils.py", "utils", ["lambdas"])


# --- normalize_state ---

def test_normalize_state_lowercases():
    df = pl.DataFrame({"state": ["Alabama"]})
    result = df.select(utils.normalize_state(pl.col("state")))["state"].to_list()
    assert result == ["alabama"]


def test_normalize_state_strips_whitespace():
    df = pl.DataFrame({"state": [" Texas "]})
    result = df.select(utils.normalize_state(pl.col("state")))["state"].to_list()
    assert result == ["texas"]


def test_normalize_state_already_normalized():
    df = pl.DataFrame({"state": ["texas"]})
    result = df.select(utils.normalize_state(pl.col("state")))["state"].to_list()
    assert result == ["texas"]


# --- expand_state_abbr ---

def test_expand_state_abbr():
    df = pl.DataFrame({"state": ["AL"]})
    result = df.select(utils.expand_state_abbr(pl.col("state")))["state"].to_list()
    assert result == ["alabama"]


def test_expand_state_abbr_case_insensitive():
    df = pl.DataFrame({"state": ["al"]})
    result = df.select(utils.expand_state_abbr(pl.col("state")))["state"].to_list()
    assert result == ["alabama"]


# --- normalize_address ---

def test_normalize_address_street():
    df = pl.DataFrame({"address": ["123 Main Street"]})
    result = df.select(utils.normalize_address(pl.col("address")))["address"].to_list()
    assert result == ["123 Main St"]


def test_normalize_address_avenue():
    df = pl.DataFrame({"address": ["456 Oak Avenue"]})
    result = df.select(utils.normalize_address(pl.col("address")))["address"].to_list()
    assert result == ["456 Oak Ave"]


# --- validate_lat_long ---

def test_validate_lat_long_in_bounds():
    df = pl.DataFrame({"latitude": [35.0], "longitude": [-90.0]})
    assert utils.validate_lat_long(df).shape[0] == 1


def test_validate_lat_long_out_of_bounds_lat():
    df = pl.DataFrame({"latitude": [0.0], "longitude": [-90.0]})
    assert utils.validate_lat_long(df).shape[0] == 0


def test_validate_lat_long_out_of_bounds_lon():
    df = pl.DataFrame({"latitude": [35.0], "longitude": [10.0]})
    assert utils.validate_lat_long(df).shape[0] == 0


def test_validate_lat_long_null_kept():
    df = pl.DataFrame({"latitude": [None], "longitude": [None]})
    assert utils.validate_lat_long(df).shape[0] == 1
