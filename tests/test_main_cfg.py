from main import build_cfg

def test_build_cfg():
    cfg = build_cfg('k','s','client',['BTC'],{'BTC':{}},True,10,0.02,1,1,0.5,-50,True,True,True,True,False)
    assert cfg['risk_pct'] == 0.02
    assert cfg['leverage'] == 10
    assert cfg['symbols'] == ['BTC']
