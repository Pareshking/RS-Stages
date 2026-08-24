import pandas as pd

from rs_stages.actions import action_for, action_reason


def row(**kwargs):
    base = {
        "Stage": "Stage 2 — Advancing",
        "RS_Score": 85,
        "U_D": 1.0,
        "Breakout": False,
        "Breakout_Confirmed": False,
        "Extended_20Pct": False,
        "Below_50DMA": False,
    }
    base.update(kwargs)
    return pd.Series(base)


def test_stage4_always_sell():
    assert action_for(row(Stage="Stage 4 — Declining", RS_Score=99)) == "SELL"


def test_stage3_low_rs_sell_otherwise_reduce():
    assert action_for(row(Stage="Stage 3 — Topping", RS_Score=49)) == "SELL"
    assert action_for(row(Stage="Stage 3 — Topping", RS_Score=90)) == "REDUCE"


def test_stage1_watch_bands():
    assert action_for(row(Stage="Stage 1 — Basing", RS_Score=90)) == "WATCH★"
    assert action_for(row(Stage="Stage 1 — Basing", RS_Score=65)) == "WATCH"
    assert action_for(row(Stage="Stage 1 — Basing", RS_Score=30)) == "AVOID"


def test_stage2_confirmed_breakout_is_star_buy():
    assert action_for(row(RS_Score=90, Breakout=True, Breakout_Confirmed=True)) == "BUY★"


def test_stage2_partial_breakout_is_buy():
    assert action_for(row(RS_Score=90, Breakout=True, Breakout_Confirmed=False)) == "BUY"


def test_stage2_distribution_reduces():
    assert action_for(row(RS_Score=95, U_D=0.69)) == "REDUCE"


def test_stage2_extension_and_50dma_are_wait():
    assert action_for(row(RS_Score=95, Extended_20Pct=True)) == "WAIT"
    assert action_for(row(RS_Score=95, Below_50DMA=True)) == "WAIT"


def test_stage2_mid_rs_does_not_buy():
    assert action_for(row(RS_Score=79, Breakout=True, Breakout_Confirmed=True)) == "WAIT"


def test_stage2_low_rs_waits():
    assert action_for(row(RS_Score=49)) == "WAIT"


def test_action_reason_respects_stage3_precedence():
    reason = action_reason(row(Stage="Stage 3 — Topping", RS_Score=90, U_D=0.5), "REDUCE")
    assert "Stage 3" in reason
    assert "RS is 50 or higher" in reason


def test_action_reason_for_stage4_does_not_claim_distribution():
    reason = action_reason(row(Stage="Stage 4 — Declining", RS_Score=99, U_D=2.0), "SELL")
    assert "Stage 4 takes precedence" in reason
