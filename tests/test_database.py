import pytest
from sqlalchemy.orm import Session

from app.database import get_db, engine, Base
from app.models import User

def test_get_db():
    """Test the get_db generator function"""
    # Get a DB session from the generator
    db = next(get_db())
    
    # Check that it's a Session instance
    assert isinstance(db, Session)
    
    # Test with a simple query to ensure it's working
    # First create a table if it doesn't exist
    Base.metadata.create_all(bind=engine)
    
    # Then perform a simple query
    users = db.query(User).all()
    
    # The query should return a list (possibly empty)
    assert isinstance(users, list)
    
    # Close the session
    db.close() 