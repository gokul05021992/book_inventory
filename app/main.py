from fastapi import FastAPI, HTTPException, Depends, status, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models import Book,User,Token,History
import jwt

# Replace 'YourSecretKey' with a secret key of your choice
SECRET_KEY = "10207229"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 

app = FastAPI()

# SQLAlchemy configuration
# DATABASE_URL = "sqlite:///./test.db"
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:00000000@localhost/fastapi"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    is_admin:bool

class UserLogin(BaseModel):
    email: str
    password: str

class BookCreate(BaseModel):
    title: str
    description: str
    author: str
    count: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT Token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Additional feature: Logout
def logout_user(db, user_id: int):
    db.query(Token).filter(Token.user_id == user_id).delete()
    db.commit()

# API routes
@app.post("/api/user/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(name=user.name, email=user.email, password=user.password,is_admin=user.is_admin)
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}

@app.post("/api/user/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(data={"sub": db_user.email})
    db_token = Token(token=access_token, user_id=db_user.id)
    db.add(db_token)
    db.commit()
    return {"access_token": access_token, "token_type": "bearer","user_name":db_user.name}

@app.post("/api/user/logout")
def logout(token: str = Depends(decode_token), db: Session = Depends(get_db)):
    user_id = token.get("sub")
    if user_id:
        logout_user(db, user_id)
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(status_code=400, detail="Invalid token")

@app.post("/api/book", status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate, db: Session = Depends(get_db), token: str = Depends(decode_token)):
    user_email = token.get("sub")
    user = db.query(User).filter(User.email == user_email).first()
    if user.is_admin:
        new_book = Book(**book.dict())
        db.add(new_book)
        db.commit()
        return {"message": "Book created successfully","username":user.name}
    else:
        raise HTTPException(status_code=401,detail="access denied")

@app.get("/api/book", response_model=None) #List[BOOK]
def get_all_books(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@app.get("/api/book/{book_id}", response_model=None) #Book
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

# Implement pagination
@app.get("/api/user/book", response_model=None) #List[Book]
def get_books_borrowed_by_user(token: str = Depends(decode_token), skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    user_email = token.get("sub")
    if user_email:
        books = db.query(Book).filter(Book.borrower_email == user_email).offset(skip).limit(limit).all()
        return books
    else:
        raise HTTPException(status_code=400, detail="Invalid token")

@app.put("/api/book/{book_id}/borrow")
def borrow_book(book_id: int, token: str = Depends(decode_token), db: Session = Depends(get_db)):
    user_email = token.get("sub")
    if user_email.is_admin:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.borrower_email:
            raise HTTPException(status_code=400, detail="Book already borrowed")
        book.borrower_email = user_email
        db.commit()
        return {"message": "Book borrowed successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid token")

@app.put("/api/book/{book_id}/return")
def return_book(book_id: int, token: str = Depends(decode_token), db: Session = Depends(get_db)):
    user_email = token.get("sub")
    if user_email:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.borrower_email != user_email:
            raise HTTPException(status_code=400, detail="You are not the borrower of this book")
        book.borrower_email = None
        db.commit()
        return {"message": "Book returned successfully"}
    else:
        raise HTTPException
    
@app.delete("/api/book/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db), token: str = Depends(decode_token)):
    user_email = token.get("sub")
    if not user_email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Retrieve user from the database using the email obtained from the token
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Check if the user is an admin
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: Only admin users can delete books")

    # Retrieve the book from the database
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Delete the book
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}

@app.get("/api/history")
def get_history(
    email: str = Query(None),
    book_title: str = Query(None),
    type: str = Query(None, title="type of action (borrow/return)"),
    date: str = Query(None),
    db: Session = Depends(get_db),
    token: str = Depends(decode_token)
):
    user_email = token.get("sub")
    if not user_email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Retrieve user from the database using the email obtained from the token
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Check if the user is an admin
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: Only admin users can access history")

    # Start building the query for retrieving history
    query = db.query(History)

    # Filter by user email if provided
    if email:
        query = query.filter(History.user_email == email)

    # Filter by book title if provided
    if book_title:
        query = query.join(Book).filter(Book.title == book_title)

    # Filter by action type if provided
    if type:
        query = query.filter(History.type == type)

    # Filter by date if provided
    if date:
        query = query.filter(History.date == date)

    # Execute the query and retrieve history records
    history_records = query.all()

    return history_records
