import polars as pl

from conftest import load_module

kaggle = load_module("lambdas/transform/kaggle.py", "kaggle")


def make_df(**overrides) -> pl.DataFrame:
    base = {
        "brokered_by": [1.0],
        "status": ["for_sale"],
        "price": [300_000.0],
        "bed": [3.0],
        "bath": [2.0],
        "acre_lot": [0.1],
        "street": [123.0],
        "city": ["Austin"],
        "state": ["Texas"],
        "zip_code": [78701.0],
        "house_size": [1500.0],
        "prev_sold_date": ["2020-01-15"],
    }
    base.update(overrides)
    return pl.DataFrame(base)


def test_drop_null_price():
    assert kaggle.clean(make_df(price=[None])).shape[0] == 0


def test_drop_zero_price():
    assert kaggle.clean(make_df(price=[0.0])).shape[0] == 0


def test_drop_negative_price():
    assert kaggle.clean(make_df(price=[-100.0])).shape[0] == 0


def test_drop_price_outlier():
    assert kaggle.clean(make_df(price=[100_000_001.0])).shape[0] == 0
