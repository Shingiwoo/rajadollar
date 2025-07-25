from risk_management.position_manager import can_open_new_position, update_open_positions

def test_position_manager():
    open_positions = []
    # Open pertama
    assert can_open_new_position("BTCUSDT", 4, 2, open_positions) == True
    update_open_positions("BTCUSDT", "long", 0.01, 30000, "open", open_positions)
    assert len(open_positions) == 1
    # Try add another coin
    assert can_open_new_position("ETHUSDT", 4, 2, open_positions) == True
    update_open_positions("ETHUSDT", "long", 0.01, 2000, "open", open_positions)
    assert len(open_positions) == 2
    # Test max_symbols
    assert can_open_new_position("DOGEUSDT", 4, 2, open_positions) == False
    # Close
    update_open_positions("BTCUSDT", "long", 0.01, 30500, "close", open_positions)
    assert len(open_positions) == 1
    print("Position Manager OK:", open_positions)

if __name__ == "__main__":
    test_position_manager()
