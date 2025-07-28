import pytest
from utils import state_manager as sm
import json
import os

def test_save_and_load(tmp_path, monkeypatch):
    """Test basic save and load functionality"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    test_data = [{"symbol": "BTC", "price": 50000.0}]
    
    # Exercise
    sm.save_state(test_data)
    loaded_data = sm.load_state()
    
    # Verify
    assert loaded_data == test_data
    assert os.path.exists(sm.STATE_FILE)
    assert os.path.exists(sm.BACKUP_FILE)

def test_load_fallback_to_backup(tmp_path, monkeypatch):
    """Test fallback to backup when main file is corrupted"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    test_data = [{"symbol": "ETH", "price": 3000.0}]
    sm.save_state(test_data)
    
    # Corrupt main file
    with open(sm.STATE_FILE, "w") as f:
        f.write("invalid json content")
    
    # Exercise
    loaded_data = sm.load_state()
    
    # Verify
    assert loaded_data == test_data

def test_load_empty_when_no_files(tmp_path, monkeypatch):
    """Test returns empty list when no state files exist"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    # Exercise
    loaded_data = sm.load_state()
    
    # Verify
    assert loaded_data == []

def test_save_atomicity(tmp_path, monkeypatch):
    """Test atomic write behavior"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    test_data = [{"symbol": "SOL", "price": 150.0}]
    
    # Exercise
    sm.save_state(test_data)
    
    # Verify atomic write
    assert not any(f.startswith('.tmp_') for f in os.listdir(tmp_path))
    assert os.path.exists(sm.STATE_FILE)
    assert os.path.exists(sm.BACKUP_FILE)

def test_delete_state(tmp_path, monkeypatch):
    """Test state deletion"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    test_data = [{"symbol": "ADA", "price": 1.2}]
    sm.save_state(test_data)
    
    # Exercise
    sm.delete_state()
    
    # Verify
    assert not os.path.exists(sm.STATE_FILE)
    assert not os.path.exists(sm.BACKUP_FILE)

def test_corrupted_backup_handling(tmp_path, monkeypatch):
    """Test handling when both files are corrupted"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    # Create corrupted files
    for filepath in [sm.STATE_FILE, sm.BACKUP_FILE]:
        with open(filepath, "w") as f:
            f.write("invalid json")
    
    # Exercise
    loaded_data = sm.load_state()
    
    # Verify
    assert loaded_data == []

def test_save_error_handling(tmp_path, monkeypatch, capsys):
    """Test error handling during save"""
    # Setup
    monkeypatch.setattr(sm, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(sm, "STATE_FILE", str(tmp_path / "active_trades.json"))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(tmp_path / "active_trades.bak.json"))
    
    # Make directory unwritable
    os.chmod(tmp_path, 0o400)
    
    # Exercise
    with pytest.raises(RuntimeError):
        sm.save_state([{"symbol": "DOT"}])
    
    # Cleanup
    os.chmod(tmp_path, 0o755)