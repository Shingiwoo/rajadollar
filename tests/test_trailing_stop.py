from risk_management.position_manager import apply_trailing_sl


def test_trailing_atr_mode():
    sl = apply_trailing_sl(
        price=105,
        entry=100,
        direction="long",
        trailing_sl=95,
        trigger_pct=1.0,
        step=2.0,
        mode="atr",
        atr=1.5,
    )
    assert sl == 102

    sl2 = apply_trailing_sl(
        price=103,
        entry=100,
        direction="long",
        trailing_sl=sl,
        trigger_pct=1.0,
        step=2.0,
        mode="atr",
        atr=1.5,
    )
    assert sl2 == sl


def test_two_stage_trailing():
    sl = apply_trailing_sl(
        price=100.6,
        entry=100,
        direction="long",
        trailing_sl=95,
        trigger_pct=1.0,
        step=0.3,
        breakeven_pct=0.5,
    )
    assert sl == 100

    sl2 = apply_trailing_sl(
        price=101,
        entry=100,
        direction="long",
        trailing_sl=sl,
        trigger_pct=1.0,
        step=0.3,
        breakeven_pct=0.5,
    )
    expected = 101 - 0.003 * 101
    assert abs(sl2 - expected) < 1e-6

    sl3 = apply_trailing_sl(
        price=100.8,
        entry=100,
        direction="long",
        trailing_sl=sl2,
        trigger_pct=1.0,
        step=0.3,
        breakeven_pct=0.5,
    )
    assert sl3 == sl2

